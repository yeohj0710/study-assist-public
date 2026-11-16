import io
import json
import subprocess
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFilter

from phone_server import MAX_QUEUED_VIEWS, AgentRouter, AgentRouterRefused, CodexSubscription, EventHistory, FrameView, QuestionView, Study, create_server, cv2, document_region, frame_signature, similar_frame, read_routing_result, haptic, haptic_trace, parse_choice, resized_jpeg


class PhoneFlowTests(unittest.TestCase):
    def test_haptic_labels_match_pulses_and_number_grammar(self):
        timings, segments = haptic_trace(10, 4)
        self.assertEqual(timings, haptic(10, 4))
        self.assertEqual(['●●', '●', '▬▬', '', '●●●●'], [part['marks'] for part in segments])
        self.assertEqual({140, 620}, set(timings[1::2]))
        self.assertEqual([0, 240, 800, 800, 240, 1500, 240, 240, 240], timings[::2])
        self.assertEqual(sum(timings), segments[-1]['to_ms'])
        self.assertEqual(1500, segments[-2]['to_ms'] - segments[-2]['from_ms'])
        for kind, expected in [('rescan', [620, 620]), ('check', [620, 140]), ('answer', [140, 140])]:
            with self.subTest(kind=kind):
                wave, _ = haptic_trace(17, 0 if kind == 'rescan' else 3, kind)
                self.assertEqual(expected, wave[1:4:2])

    def test_solved_answers_never_wait_for_page_or_earlier_number(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        player = study.player

        def show(page, now):
            player.observe('책', page, now)
            study.last_routed_page = page
            player.observe('책', page, now + 2)

        def poll(now, ack=None):
            with patch('phone_server.time.monotonic', return_value=now):
                return study.poll('run', ack, ack is not None).get('packet')

        show(1, 100)
        show(2, 103)
        study.pending.add(('run', 2, 8))
        player.save('책', (2,), 10, 3)
        current = poll(105)
        self.assertEqual(10, current['question'])
        player.save('책', (1,), 3, 2)
        player.save('책', (2,), 8, 3)
        study.pending.clear()
        self.assertIsNone(poll(115, current['id']))
        other_page = poll(117)
        self.assertEqual(3, other_page['question'])
        self.assertEqual('●●', other_page['segments'][0]['marks'])
        self.assertIsNone(poll(127, other_page['id']))
        earlier_number = poll(129)
        self.assertEqual(8, earlier_number['question'])
        self.assertIsNone(poll(139, earlier_number['id']))
        show(1, 150)
        self.assertIsNone(poll(152))
        show(2, 153)
        self.assertIsNone(poll(155))

    def test_stop_drains_all_views_and_delivers_each_answer_once(self):
        def route(_stream, data):
            question = int(data)
            view = QuestionView(False, f'question {question}', True)
            return FrameView(question, False, {question: view})

        study = Study(lambda _photos, question: (question - 1) % 5 + 1, 1, False, route)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        with patch.object(study.routing_pool, 'submit') as dispatch:
            for number in range(1, 11):
                study.queue_view('run', number, str(number).encode(), number)
            self.assertTrue(study.poll('run', None, False, draining=True)['waiting'])
            for claim in range(10):
                handler, *args = dispatch.call_args_list[claim].args
                handler(*args)
            self.assertEqual(10, dispatch.call_count)
        self.assertFalse(study.queued_views)
        self.assertEqual(set(range(1, 11)), study.detected_questions)
        study.pool.shutdown()
        study.player.observe('책', 10, 10)
        delivered = {}
        ack = None
        with patch('phone_server.time.monotonic', side_effect=range(100, 1000, 20)):
            for _ in range(21):
                update = study.poll('run', ack, ack is not None, draining=True)
                signal = update.get('packet')
                if signal:
                    delivered[signal['question']] = signal['answer']
                ack = signal['id'] if signal else None
                if not update['waiting']:
                    break
        self.assertEqual({number: (number - 1) % 5 + 1 for number in range(1, 11)}, delivered)
        self.assertEqual(10, len(study.player.answers))
        self.assertEqual(0, update['review_needed'])

    def test_coverage_lists_unanswered_and_missing_numbers(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.detected_questions.update((1, 3))
        update = study.poll('run', None, False, draining=True)
        self.assertFalse(update['waiting'])
        self.assertEqual(3, update['review_needed'])
        self.assertIn('다시 촬영할 문항 1, 3', update['events'][0])
        self.assertIn('번호가 확인되지 않은 문항 2', update['events'][1])

    def test_rescan_signal_covers_detected_incomplete_and_unseen_numbers(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.detected_questions.update((1, 3))
        signals = []
        ack = None
        with patch('phone_server.time.monotonic', side_effect=range(100, 1000, 20)):
            for _ in range(8):
                update = study.poll('run', ack, ack is not None, draining=True, notices=True)
                packet = update.get('packet')
                if packet:
                    signals.append((packet['kind'], packet['question'], packet['segments'][0]['marks']))
                ack = packet['id'] if packet else None
                if not update['waiting']:
                    break
        self.assertEqual([('rescan', 1, '▬▬'), ('rescan', 2, '▬▬'), ('rescan', 3, '▬▬')], signals)
        self.assertFalse(update['waiting'])

    def test_expected_range_reports_unseen_end_even_if_only_first_half_was_detected(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.detected_questions.update(range(1, 6))
        for number in range(1, 6):
            study.player.save('책', (1,), number, 1)
            study.player.delivered.add(('책', 1, number))
        first = study.poll('run', None, False, draining=True, notices=True, expected=(1, 10))
        self.assertEqual(6, first['packet']['question'])
        self.assertTrue(first['waiting'])
        self.assertIn('번호가 확인되지 않은 문항 6, 7, 8, 9, 10', ' '.join(first['events']))

    def test_model_fallback_runs_only_on_confirmed_quota_error(self):
        from phone_server import ModelQuotaExhausted, ResilientModel

        class Primary:
            failure = ModelQuotaExhausted('test quota')

            def solve(self, _photos, _question):
                raise self.failure

        class Reserve:
            def solve(self, _photos, question):
                return question

        model = ResilientModel(Primary(), Reserve)
        self.assertEqual(3, model.solve((b'one',), 3))
        self.assertEqual(4, model.solve((b'two',), 4))
        rejected = Primary()
        rejected.failure = AgentRouterRefused('rejected')
        with self.assertRaises(AgentRouterRefused):
            ResilientModel(rejected, Reserve).solve((b'one',), 3)

    def test_wrong_check_needs_two_distinct_frames_and_signals_once(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.player.save('책', (1,), 3, 4)
        study.player.delivered.add(('책', 1, 3))
        study.last_routed_page = 1
        study.player.observe('책', 1, 100)
        study.observe_mark(1, 3, 2, b'photo10', 100)
        study.observe_mark(1, 3, 2, b'photo10', 101)
        self.assertIsNone(study.mark_notice(101, 1))
        study.observe_mark(1, 3, 0, b'photo11', 102)
        study.observe_mark(1, 3, 2, b'photo12', 103)
        self.assertIsNone(study.mark_notice(103, 1))
        study.observe_mark(1, 3, 2, b'photo13', 104)
        with patch('phone_server.time.monotonic', side_effect=(105, 114, 131)):
            first = study.poll('run', None, False, notices=True)['packet']
            self.assertEqual(('check', 3, 4, 2), (first['kind'], first['question'], first['answer'], first['marked']))
            self.assertEqual('▬●', first['segments'][0]['marks'])
            self.assertNotIn('packet', study.poll('run', first['id'], True, notices=True))
            self.assertNotIn('packet', study.poll('run', None, False, notices=True))
        study.observe_mark(1, 3, 4, b'photo14', 132)
        self.assertIsNone(study.mark_notice(133, 1))

    def test_ambiguous_handwriting_is_not_a_marked_choice(self):
        entry = {'number': 3, 'marked_choice': 2, 'mark_clear': False}
        self.assertEqual(0, read_routing_result({'study_page': True, 'questions': [entry]}).questions[3].marked_choice)
        entry['mark_clear'] = True
        self.assertEqual(2, read_routing_result({'study_page': True, 'questions': [entry]}).questions[3].marked_choice)

    def test_route_backpressure_reduces_capture_rate_before_eviction(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        self.assertEqual(3000, study.frame_result(1, False, 0, '사진', False)['interval_ms'])
        for group in range(MAX_QUEUED_VIEWS // 2):
            study.queue_view('run', group, b'photo', group)
        result = study.frame_result(1, False, 1, '사진', False)
        self.assertEqual(6000, result['interval_ms'])
        self.assertFalse(result['steady'])
        self.assertEqual(0, study.overflow_views)
        self.assertIn('문항 판별 대기', result['status'])

    def test_two_waiting_photos_start_together(self):
        study = Study(None, 1, False, batch_router=lambda *_: ())
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.queue_view('run', 1, b'one', 1)
        study.queue_view('run', 2, b'two', 2)
        study.route_retry_at = 11
        with patch.object(study.routing_pool, 'submit') as work:
            study.schedule_view(10)
        handler, views = work.call_args.args
        self.assertEqual(handler, study.route_batch)
        self.assertEqual([view[1] for view in views], [1, 2])

    def test_route_retry_restores_photo_order(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.queue_view('run', 3, b'three', 3)
        study.route('run', 1, b'one', 1, batch=True, failure=OSError('sample failed'))
        study.route('run', 2, b'two', 2, batch=True, failure=OSError('sample failed'))
        self.assertEqual(list(study.queued_views), [1, 2, 3])

    def test_unreadable_new_heading_does_not_hide_previous_answers(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.active_subject = '국어'
        study.detected_questions = {7}
        study.update_scope(FrameView(1, False, {}, subject='수리'), 10)
        self.assertEqual(study.active_subject, '국어')
        self.assertEqual(study.detected_questions, {7})
        study.update_scope(FrameView(1, False, {1: QuestionView(False, '읽힌새문항')}, subject='수리'), 11)
        self.assertEqual(study.active_subject, '수리')
        self.assertFalse(study.detected_questions)

    def test_backlog_groups_multiple_photos_without_changing_fragment_order(self):
        routed = []

        def batch(_stream, photos):
            routed.append(photos)
            return tuple(FrameView(int(data), False, {int(data): QuestionView(False, '')}) for data in photos)

        study = Study(lambda _photos, n: 1, 1, False, router=None, batch_router=batch)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        with patch.object(study.routing_pool, 'submit') as work:
            for index in range(1, 4):
                study.queue_view('run', index, str(index).encode(), index)
            study.schedule_view(10)
            fn, *args = work.call_args.args
            fn(*args)
        self.assertEqual([(b'1', b'2', b'3')], routed)
        self.assertEqual([1, 2, 3], list(study.details))

    def test_a_sharper_frame_reopens_a_failed_read_of_the_same_scene(self):
        image = Image.new('RGB', (768, 576), 'white')
        pen = ImageDraw.Draw(image)
        for y in range(50, 540, 20):
            for x in range(55, 700, 22):
                pen.rectangle((x, y, x + 15, y + 5), fill='black')

        def jpeg(photo):
            out = io.BytesIO()
            photo.save(out, 'JPEG', quality=93)
            return out.getvalue()

        study = Study(None, 1, False, router=lambda *_: None)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        blurry, sharp = jpeg(image.filter(ImageFilter.GaussianBlur(5))), jpeg(image)
        with patch('phone_server.similar_frame', return_value=True), patch('phone_server.time.monotonic', return_value=10), \
                patch.object(study.routing_pool, 'submit') as dispatch:
            study.upload('run', blurry)
            fn, *args = dispatch.call_args.args
            fn(*args)
            study.upload('run', blurry)
            self.assertEqual(1, dispatch.call_count)
            with patch('phone_server.time.monotonic', return_value=30):
                study.upload('run', sharp)
            self.assertEqual(2, dispatch.call_count)


    @unittest.skipIf(cv2 is None, 'optional OpenCV is missing')
    def test_wide_angle_document_can_be_rectified_without_using_a_cut_page(self):
        from phone_server import document_geometry, perspective_image

        photo = Image.new('RGB', (1200, 900), (66, 58, 50))
        draw = ImageDraw.Draw(photo)
        draw.polygon([(430, 182), (734, 182), (1015, 678), (193, 678)], fill=(180, 199, 238))
        for y in range(215, 670, 28):
            a = int(430 + (193 - 430) * (y - 182) / 496) + 50
            b = int(734 + (1015 - 734) * (y - 182) / 496) - 50
            for x in range(a, b, 19):
                draw.rectangle((x, y, x + 11, y + 5), fill=(28, 39, 61))
        crop, quad = document_geometry(photo)
        self.assertIsNotNone(crop)
        self.assertIsNotNone(quad)
        corrected = perspective_image(photo, quad, 1800)
        self.assertGreater(corrected.width, 600)
        self.assertGreater(corrected.height, 440)
        self.assertIsNone(document_geometry(photo.crop((0, 230, 1060, 720)))[1])

    @unittest.skipIf(cv2 is None, 'optional OpenCV is missing')
    def test_tab_crop_includes_visible_text_and_removes_desk(self):
        image = Image.new('RGB', (1000, 800), (220, 196, 151))
        draw = ImageDraw.Draw(image)
        draw.polygon([(272, 325), (630, 305), (805, 744), (196, 752)], fill=(162, 181, 238))
        for y in range(360, 705, 17):
            for x in range(305, 620, 22):
                draw.rectangle((x, y, x + 14, y + 4), fill=(25, 28, 42))
        x0, y0, x1, y1 = document_region(image)
        self.assertLessEqual(x0, 196)
        self.assertLessEqual(y0, 305)
        self.assertGreaterEqual(x1, 805)
        self.assertGreaterEqual(y1, 752)
        self.assertGreater(y0, 180)
    def test_numbered_views_join_by_identity_and_choice_coverage(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        with patch.object(study.pool, 'submit') as solve:
            head = QuestionView(False, '같은문항첫구절', False, True, (1, 2), False)
            tail = QuestionView(False, '', False, False, (3, 4, 5), True)
            study.forward('run', 1, b'question and options 1 2', FrameView(42, False, {6: head}), 10, 1)
            solve.assert_not_called()
            study.forward('run', 2, b'options 3 4 5', FrameView(42, False, {6: tail}), 15, 2)
            solve.assert_called_once_with(study.solve, ('run', 1, 6), (1, 2),
                                         (b'question and options 1 2', b'options 3 4 5'))

    def test_long_passage_keeps_five_ordered_pieces_through_the_last_choice(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        photos = tuple(bytes([index]) for index in range(1, 6))
        with patch.object(study.pool, 'submit') as solve:
            study.forward('run', 1, photos[0], FrameView(10, False, {8: QuestionView(True, 'longpassage')}), 10, 1)
            for i in range(1, 4):
                study.forward('run', i + 1, photos[i], FrameView(10, True, {}, 8, True, False), 10 + i, i + 1)
                solve.assert_not_called()
            study.forward('run', 5, photos[4], FrameView(11, True, {}, 8, False, True), 14, 5)
            solve.assert_called_once_with(study.solve, ('run', 1, 8), (1, 2, 3, 4, 5), photos)

    def test_only_listening_module_ids_can_solve_with_printed_options_absent(self):
        submitted = []
        study = Study(lambda photos, question: submitted.append((photos, question)) or 4, 1, False,
                      listening_questions={7})
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        view = QuestionView(True, 'listeningquestion', False)
        study.forward('run', 1, b'question-numbers', FrameView(1, False, {7: view, 8: view}), 10, 1)
        study.pool.shutdown()
        self.assertEqual([((b'question-numbers',), 7)], submitted)
        self.assertEqual(4, study.player.answers[('책', 1, 7)][1])

    def test_log_pages_are_ordered_and_do_not_overlap(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / 'events.sqlite3'
            history = EventHistory(file)
            for i in range(120):
                history.append(f'event {i + 1}')
            latest = history.page(None)
            self.assertEqual(list(range(71, 121)), [row['id'] for row in latest['entries']])
            self.assertTrue(latest['more'])
            older = EventHistory(file).page(71)
            self.assertEqual(list(range(21, 71)), [row['id'] for row in older['entries']])
            earliest = history.page(21)
            self.assertEqual(20, len(earliest['entries']))
            self.assertFalse(earliest['more'])
    def test_visible_question_end_is_required_before_spawning_solver(self):
        packed = read_routing_result({'study_page': True, 'page': 42, 'carry_in': False, 'questions': [
            {'number': 4, 'carry_out': False, 'stem_readable': True, 'end_visible': True,
             'visible_choices': [1, 2, 3, 4, 5]},
            {'number': 5, 'carry_out': False, 'stem_readable': True, 'end_visible': False,
             'visible_choices': [1, 2, 3, 4]},
        ]})
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        with patch.object(study.pool, 'submit') as submit:
            study.forward('run', 1, b'exercise photo', packed, 10, 1)
            submit.assert_called_once_with(study.solve, ('run', 1, 4), (1,), (b'exercise photo',))

    def test_same_question_without_printed_page_uses_solved_answer(self):
        view = FrameView(None, False, {34: QuestionView(False, '공동체 참여가 필요한 이유')})
        study = Study(None, 1, False, router=lambda *_: view)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.details[1] = view
        study.player.save('책', (1,), 34, 3)
        with patch.object(study.pool, 'submit') as solve:
            study.route('run', 4, b'new angle', 12)
            self.assertEqual(1, study.aliases[4])
            solve.assert_not_called()

    def test_joins_column_and_page_fragments_without_reordering(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        with patch.object(study.pool, 'submit') as solve:
            study.forward('run', 1, b'left column', FrameView(42, False, {3: QuestionView(True, '관련 지문')}), 10, 1)
            study.forward('run', 1, b'right column', FrameView(42, True, {}, 3, True), 13, 2)
            solve.assert_not_called()
            study.forward('run', 3, b'next page', FrameView(43, True, {}, 3), 16, 3)
            solve.assert_called_once_with(study.solve, ('run', 1, 3), (1, 3),
                                         (b'left column', b'right column', b'next page'))

    def test_does_not_join_an_unrelated_page(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        with patch.object(study.pool, 'submit') as solve:
            study.forward('run', 1, b'first', FrameView(42, False, {3: QuestionView(True, '')}), 10, 1)
            study.forward('run', 7, b'wrong page', FrameView(45, True, {}, 3), 13, 7)
            solve.assert_not_called()

    def test_repeated_frame_signal_keeps_replay_fresh_without_another_photo(self):
        study = Study(None, 1, True)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.details[1] = FrameView(1, False, {})
        study.player.observe('책', 1, 0)
        study.player.observe('책', 1, 3)
        with patch('phone_server.time.monotonic', return_value=9):
            self.assertTrue(study.seen_same('run'))
            self.assertFalse(study.seen_same('other'))
        self.assertEqual(9, study.player.last_frame_at)
        self.assertEqual(0, study.received)
        with patch('phone_server.time.monotonic', return_value=22):
            self.assertFalse(study.seen_same('run'))

    def test_matches_numbered_continuation_after_visiting_other_page(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        with patch.object(study.pool, 'submit') as solve:
            study.forward('run', 1, b'first', FrameView(42, False, {3: QuestionView(True, '')}), 10, 1)
            study.forward('run', 7, b'other', FrameView(50, False, {8: QuestionView(True, '')}), 13, 7)
            study.forward('run', 2, b'end', FrameView(43, True, {}, 3), 100, 2)
            solve.assert_called_once_with(study.solve, ('run', 1, 3), (1, 2), (b'first', b'end'))

    def test_codex_uses_signed_in_provider_and_fresh_session(self):
        with patch.dict('phone_server.os.environ', {'OPENAI_API_KEY': 'skip', 'CODEX_API_KEY': 'skip'}):
            with patch('phone_server.shutil.which', return_value='codex.exe'):
                client = CodexSubscription()

        def fake_run(argv, **kwargs):
            self.assertIn('--ephemeral', argv)
            self.assertIn('model_provider="openai"', argv)
            self.assertIn('model_reasoning_effort="high"', argv)
            self.assertNotIn('OPENAI_API_KEY', kwargs['env'])
            self.assertNotIn('CODEX_API_KEY', kwargs['env'])
            self.assertEqual(b'sample-jpeg', Path(argv[argv.index('-i') + 1]).read_bytes())
            Path(argv[argv.index('-o') + 1]).write_text('{"question":3,"choice":4,"status":"ok"}', encoding='utf-8')
            return subprocess.CompletedProcess(argv, 0, stdout='', stderr='')

        with patch('phone_server.subprocess.run', side_effect=fake_run) as runs:
            self.assertEqual(4, client.solve((b'sample-jpeg',), 3))
            runs.assert_called_once()

    def test_agentrouter_sends_only_input_images_and_schema(self):
        client = AgentRouter.__new__(AgentRouter)
        client.exe = 'codex.exe'
        client.env = {'CODEX_HOME': 'isolated-test-home'}
        client.accounts = [('first', 'test-key')]
        client.depleted = set()
        client.account_lock = threading.Lock()

        def fake_run(argv, **kwargs):
            self.assertIn('--ephemeral', argv)
            self.assertIn('gpt-6.1-sol', argv)
            self.assertIn('model_reasoning_effort="high"', argv)
            self.assertEqual(dict(client.env, STUDY_AGENTROUTER_KEY='test-key'), kwargs['env'])
            self.assertEqual(b'sample-jpeg', Path(argv[argv.index('-i') + 1]).read_bytes())
            result = {'question': 3, 'choice': 4, 'status': 'ok'}
            Path(argv[argv.index('-o') + 1]).write_text(json.dumps(result), encoding='utf-8')
            return subprocess.CompletedProcess(argv, 0, stdout='', stderr='')

        with patch('phone_server.subprocess.run', side_effect=fake_run):
            self.assertEqual(4, client.solve((b'sample-jpeg',), 3))

    def test_only_exhausted_credit_switches_agentrouter_key(self):
        for error in ('insufficient_user_quota', 'content-blocked', 'HTTP 429 rate limit'):
            with self.subTest(error=error):
                client = AgentRouter.__new__(AgentRouter)
                client.exe = 'codex.exe'
                client.env = {}
                client.accounts = [('first', 'key1'), ('second', 'key2')]
                client.depleted = set()
                client.account_lock = threading.Lock()

                def fake_run(argv, **kwargs):
                    if kwargs['env']['STUDY_AGENTROUTER_KEY'] == 'key1':
                        return subprocess.CompletedProcess(argv, 1, stdout=error, stderr='')
                    result = {'question': 3, 'choice': 4, 'status': 'ok'}
                    Path(argv[argv.index('-o') + 1]).write_text(json.dumps(result), encoding='utf-8')
                    return subprocess.CompletedProcess(argv, 0, stdout='', stderr='')

                with patch('phone_server.subprocess.run', side_effect=fake_run) as runs:
                    if error == 'insufficient_user_quota':
                        self.assertEqual(4, client.solve((b'sample-jpeg',), 3))
                        self.assertEqual(2, runs.call_count)
                    else:
                        with self.assertRaises(AgentRouterRefused if error == 'content-blocked' else OSError):
                            client.solve((b'sample-jpeg',), 3)
                        runs.assert_called_once()

    def test_model_copy_is_bounded_and_keeps_orientation(self):
        source = io.BytesIO()
        original = Image.new('RGB', (2400, 1800), 'white')
        exif = original.getexif()
        exif[274] = 6
        original.save(source, 'JPEG', exif=exif)
        with Image.open(io.BytesIO(resized_jpeg(source.getvalue(), 1600))) as small:
            self.assertEqual((1200, 1600), small.size)

    def test_static_page_stays_recognized_at_slower_capture_rate(self):
        study = Study(None, 1, True)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        jpeg = io.BytesIO()
        Image.new('L', (64, 64), 150).save(jpeg, 'JPEG')
        for t in (10, 13, 19.4):
            with patch('phone_server.time.monotonic', return_value=t):
                response = study.upload('run', jpeg.getvalue())
            self.assertEqual(t != 10, response['steady'])
        self.assertEqual(2, study.player.frames)

    def test_unstable_frames_still_classify_and_deliver_solved_answer(self):
        started = threading.Event()
        allow_router = threading.Event()
        routed = threading.Event()

        def route(_stream, _photo):
            started.set()
            if not allow_router.wait(2):
                raise RuntimeError('routing test timed out')
            routed.set()
            return FrameView(1, False, {3: QuestionView(False, '')})

        study = Study(lambda _photos, _question: 4, 1, False, router=route)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        self.addCleanup(allow_router.set)
        for color in ('black', 'white'):
            jpeg = io.BytesIO()
            img = Image.new('L', (320, 400), 200)
            ImageDraw.Draw(img).rectangle((5, 20, 240, 170), fill=color)
            img.save(jpeg, 'JPEG')
            study.upload('run', jpeg.getvalue())
        self.assertEqual(1, study.player.frames)
        self.assertTrue(started.wait(1), '교재 판별이 시작되어야 합니다')
        allow_router.set()
        study.routing_pool.shutdown()
        study.pool.shutdown()
        self.assertTrue(routed.is_set())
        result = study.poll('run', None, False)
        self.assertEqual(haptic(3, 4), result['packet']['timings'])
        self.assertTrue(any('풀이 시작' in item for item in result['events']))
        self.assertEqual((3, 4), (result['packet']['question'], result['packet']['answer']))
        study.poll('run', result['packet']['id'], True)
        self.assertTrue(any('앱 신호 요청 완료' in item for item in study.poll('run', None, False)['events']))
        self.assertNotIn('packet', study.poll('run', None, False))

    def test_answer_keeps_same_packet_after_page_turn(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.player.save('책', (1,), 3, 4)
        study.last_routed_page = 1
        study.player.observe('책', 1, 0)
        study.player.observe('책', 1, 3)
        with patch('phone_server.time.monotonic', return_value=3):
            before = study.poll('run', None, False)
        study.player.observe('책', 2, 4)
        study.player.observe('책', 2, 6)
        with patch('phone_server.time.monotonic', return_value=6):
            after = study.poll('run', None, False)
        self.assertTrue(after['valid'])
        self.assertEqual(before['packet']['id'], after['packet']['id'])
        self.assertEqual(before['visit'], after['visit'])

    def test_stopped_capture_finishes_pending_answer_without_replay(self):
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        key = ('run', 1, 3)
        study.pending.add(key)
        self.assertTrue(study.poll('run', None, False, draining=True)['waiting'])
        study.pending.remove(key)
        study.player.save('책', (1,), 3, 4)
        study.last_routed_page = 1
        study.player.observe('책', 1, 0)
        study.player.observe('책', 1, 3)
        with patch('phone_server.time.monotonic', return_value=3):
            result = study.poll('run', None, False, draining=True)
        self.assertTrue(result['waiting'])
        with patch('phone_server.time.monotonic', return_value=9):
            self.assertFalse(study.poll('run', result['packet']['id'], True, draining=True)['waiting'])
        study.player.observe('책', 1, 24)
        study.player.observe('책', 1, 27)
        with patch('phone_server.time.monotonic', return_value=27):
            self.assertNotIn('packet', study.poll('run', None, False, draining=True))
            self.assertNotIn('packet', study.poll('run', None, False))

    def test_received_photo_can_be_viewed_on_pc_and_from_authenticated_app(self):
        with tempfile.TemporaryDirectory() as folder:
            study = Study(None, 1, True)
            self.addCleanup(study.pool.shutdown)
            self.addCleanup(study.routing_pool.shutdown)
            with create_server('127.0.0.1', 0, 'test-token', study, photo_dir=Path(folder)) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                conn = HTTPConnection(*server.server_address, timeout=3)
                headers = {'Authorization': 'Bearer test-token', 'X-Study-Session': str(uuid4())}
                try:
                    frames = []
                    for color in ('black', 'white'):
                        jpeg = io.BytesIO()
                        image = Image.new('RGB', (64, 64), 'gray')
                        ImageDraw.Draw(image).rectangle((0, 0, 31, 31), fill=color)
                        image.save(jpeg, 'JPEG')
                        data = jpeg.getvalue()
                        frames.append(data)
                        conn.request('POST', '/frame', data, headers)
                        response = conn.getresponse()
                        self.assertEqual(200, response.status, response.read())
                        response.read()
                    conn.request('GET', '/photos')
                    response = conn.getresponse()
                    self.assertEqual(401, response.status)
                    response.read()
                    conn.request('GET', '/photos', headers=headers)
                    photos = json.loads(conn.getresponse().read())['photos']
                    self.assertEqual(2, len(photos))
                    latest = photos[0]
                    self.assertEqual(frames[-1], (Path(folder) / latest).read_bytes())
                    conn.request('GET', '/photos/' + latest, headers=headers)
                    response = conn.getresponse()
                    self.assertEqual('image/jpeg', response.getheader('Content-Type'))
                    self.assertEqual(frames[-1], response.read())
                    conn.request('GET', '/photos/' + latest + '/thumbnail', headers=headers)
                    out = conn.getresponse()
                    self.assertEqual(200, out.status)
                    with Image.open(io.BytesIO(out.read())) as thumbnail:
                        self.assertEqual((64, 64), thumbnail.size)
                    conn.request('GET', '/photos/../connection.key', headers=headers)
                    response = conn.getresponse()
                    self.assertEqual(404, response.status)
                    response.read()
                finally:
                    conn.close()
                    server.shutdown()
                    thread.join()

    def test_archives_first_and_sampled_still_photos(self):
        study = Study(None, 1, True)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        jpeg = io.BytesIO()
        Image.new('L', (64, 64), 150).save(jpeg, 'JPEG')
        for stamp, keep in ((10, True), (13, True), (19, False), (67, False), (73, True)):
            with patch('phone_server.time.monotonic', return_value=stamp):
                result = study.upload('run', jpeg.getvalue())
            self.assertEqual(keep, result['keep_photo'])

    def test_twelve_hour_static_capture_uses_one_group_and_minute_samples(self):
        study = Study(None, 1, True)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        signature = bytes(48 * 48)
        kept = 0
        with patch('phone_server.frame_signature', return_value=signature), patch('builtins.print'), \
             patch('phone_server.time.monotonic') as clock:
            for stamp in range(0, 12 * 60 * 60, 6):
                clock.return_value = stamp
                kept += study.upload('run', b'fixture')['keep_photo']
        self.assertEqual(7200, study.received)
        self.assertEqual(1, len(study.sheets))
        self.assertLessEqual(kept, 722)

    def test_only_visually_changed_frames_need_the_coordinator(self):
        def frame(lines):
            source = Image.new('L', (320, 400), 250)
            draw = ImageDraw.Draw(source)
            for y in lines:
                draw.line((44, y, 245, y), fill=30, width=7)
            output = io.BytesIO()
            source.save(output, 'JPEG')
            return frame_signature(output.getvalue())
        first = frame(range(35, 175, 15))
        self.assertTrue(similar_frame(first, frame(range(36, 176, 15))))
        self.assertFalse(similar_frame(first, frame(range(206, 376, 15))))
        self.assertFalse(similar_frame(frame((49, 64, 81)), frame((264, 286, 309))))
        white = bytes([250] * 2304)
        sparse_ink = bytes([216] * 114 + [250] * (2304 - 114))
        self.assertFalse(similar_frame(white, sparse_ink))

    def test_partial_page_and_choice_validation(self):
        route = read_routing_result({'study_page': True, 'page': 42, 'carry_in': True, 'questions': [
            {'number': 17, 'carry_out': True}, {'number': 18, 'carry_out': False}]})
        self.assertEqual(FrameView(42, True, {17: QuestionView(True, '', False), 18: QuestionView(False, '', False)},
                                   continuation_end_visible=False), route)
        self.assertIsNone(read_routing_result({'study_page': False, 'page': 0, 'carry_in': False, 'questions': []}))
        self.assertEqual(3, parse_choice({'question': 17, 'status': 'ok', 'choice': 3}, 17))
        self.assertIsNone(parse_choice({'question': 18, 'status': 'ok', 'choice': 3}, 17))
        self.assertIsNone(parse_choice({'question': 17, 'status': 'incomplete', 'choice': 3}, 17))
        self.assertIsNone(parse_choice({'question': 17, 'status': 'ok', 'choice': True}, 17))

    def test_timeline_distinguishes_question_and_choice(self):
        for question in (3, 17, 71, 999):
            for choice in range(1, 6):
                with self.subTest(question=question, choice=choice):
                    wave = haptic(question, choice)
                    pulses = wave[1::2]
                    gaps = wave[::2]
                    marker = gaps.index(1500)
                    self.assertEqual(1, gaps.count(1500))
                    self.assertEqual(len(str(question)), gaps[:marker].count(800))
                    self.assertEqual([140] * choice, pulses[marker:])
                    self.assertLessEqual(len(wave), 46)
        self.assertNotEqual(haptic(17, 3), haptic(71, 3))

    def test_routes_confirmed_page_after_one_later_unstable_frame(self):
        study = Study(None, 1, False, router=lambda _stream, _photo: FrameView(1, False, {3: QuestionView(False, '')}))
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = 'run'
        study.player.observe('책', 1, 0)
        study.player.observe('책', 1, 3)
        study.player.observe('책', 2, 6)
        photo = b'confirmed still image'
        with patch.object(study, 'submit') as submit:
            study.route('run', 1, photo, 3)
        submit.assert_called_once_with('run', (1,), 3, (photo,), (1,))


if __name__ == '__main__':
    unittest.main()
