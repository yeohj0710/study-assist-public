import io
import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import time
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw

from listening_source import QuestionWindow, transcribe_questions
from phone_server import EventHistory, FrameView, PhotoArchive, QuestionView, Study, create_server, cv2, document_region, read_routing_result, same_page


class Recorder:
    def __init__(self):
        self.events = []

    def emit(self, stage, status, **data):
        self.events.append(dict(stage=stage, status=status, **data))


class StudyTraceTests(unittest.TestCase):
    def test_study_exposes_photo_route_solve_and_phone_ack(self):
        recorder = Recorder()
        view = FrameView(1, False, {2: QuestionView(False, "question")})
        study = Study(lambda photos, question: 4, 1, False, lambda stream, photo: view, monitor=recorder)
        self.addCleanup(study.pool.shutdown, wait=True)
        self.addCleanup(study.routing_pool.shutdown, wait=True)
        image = io.BytesIO()
        Image.new("RGB", (320, 240), "white").save(image, format="JPEG")
        study.upload("practice", image.getvalue())
        deadline = time.monotonic() + 3
        packet = None
        while time.monotonic() < deadline:
            packet = study.poll("practice", None, False, draining=True).get("packet")
            if packet:
                break
            time.sleep(.015)
        self.assertIsNotNone(packet)
        study.poll("practice", packet["id"], True, draining=True)
        event_types = {(e["stage"], e["status"]) for e in recorder.events}
        self.assertTrue({("capture", "received"), ("route", "done"), ("solve", "queued"),
                         ("solve", "running"), ("solve", "done"), ("delivery", "acknowledged")} <= event_types)
        solved = next(e for e in recorder.events if e["stage"] == "solve" and e["status"] == "done")
        self.assertEqual((solved["question"], solved["answer"], solved["run"]), (2, 4, "practice"))

    def test_filters_nonstudy_and_keeps_only_new_question_evidence(self):
        source = b"camera-frame"
        outcomes = [
            ({"study_page": False, "non_study_scene": True}, 0),
            ({"study_page": False, "non_study_scene": False}, 0),
            ({"study_page": True, "carry_in": True}, 0),
            ({"study_page": True, "questions": [{"number": 2}]}, 0),
            ({"study_page": True, "questions": [{"number": 2, "anchor": "실제로 보이는 지문"}]}, 1),
        ]
        for payload, expected in outcomes:
            with self.subTest(payload=payload), TemporaryDirectory() as directory:
                archive = PhotoArchive(Path(directory))
                study = Study(None, 1, False, lambda stream, photo: read_routing_result(payload))
                try:
                    study.stream = "practice"
                    study.archive = archive
                    study.route("practice", 1, source, time.monotonic())
                    self.assertEqual(expected, archive.count("practice"))
                finally:
                    study.pool.shutdown()
                    study.routing_pool.shutdown()

    def test_route_source_fragment_and_verified_solver(self):
        from phone_server import MONITOR_CONTEXT, PhotoModel, different_documents, monitor_context
        def page(source):
            return read_routing_result({"study_page": True, "source": source, "questions": []})
        self.assertFalse(different_documents(page("2026학년도 9월 모의평가"), page("대학수학능력시험 9월 모의평가")))
        self.assertTrue(different_documents(page("2026학년도 9월 모의평가"), page("2027학년도 9월 모의평가")))
        class FakeModel(PhotoModel):
            def request(self, task, effort, schema, prompt, photos, timeout):
                return self.response
        image = io.BytesIO()
        Image.new("RGB", (320, 240), "white").save(image, format="JPEG")
        model = FakeModel()
        model.response = {"question": 3, "status": "ok", "choice": 4, "explanation": "",
                          "anchor_seen": "실제로 보이는 첫 번째 구절", "choices_seen": [1, 2, 3, 4, 5]}
        with monitor_context(Recorder(), verify_anchor="실제로보이는첫번째구절"):
            self.assertEqual(model.solve((image.getvalue(),), 3), 4)
            model.response["choices_seen"].pop()
            self.assertIsNone(model.solve((image.getvalue(),), 3))
            model.response["choices_seen"].append(5)
            model.response["anchor_seen"] = "완전히 다른 문항의 첫부분"
            self.assertIsNone(model.solve((image.getvalue(),), 3))
        done = threading.Event()
        calls = []
        def solver(photos, question):
            calls.append((question, MONITOR_CONTEXT.get()[1]["verify_anchor"]))
            done.set()
            return None
        ready_to_verify = QuestionView(False, "실제로보이는첫번째구절", False, False, (1, 2, 3, 4, 5), True)
        missing_choice = ready_to_verify._replace(choices=(1, 2, 3, 4), end_visible=False)
        details = FrameView(1, False, {3: ready_to_verify, 14: missing_choice})
        study = Study(solver, 1, False, lambda *_: details, model_settings=object())
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = "practice"
        study.route(study.stream, 1, image.getvalue(), time.monotonic())
        self.assertTrue(done.wait(3))
        study.route(study.stream, 2, image.getvalue(), time.monotonic())
        self.assertEqual(calls, [(3, "실제로보이는첫번째구절")])

    def test_clear_progress_requires_key_and_does_not_clear_live_work(self):
        with TemporaryDirectory() as directory:
            history = EventHistory(Path(directory) / "study.sqlite3")
            study = Study(None, 1, True, event_history=history)
            self.addCleanup(study.pool.shutdown)
            self.addCleanup(study.routing_pool.shutdown)
            study.stream = "a" * 36
            study.pending.add((study.stream, 1, 1))
            study.record("어제 기록")
            before = study.next_event
            with create_server("127.0.0.1", 0, "token", study) as server:
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}/logs/clear"
                    with self.assertRaises(HTTPError) as denied:
                        urlopen(Request(url, data=b""), timeout=3)
                    self.assertEqual(401, denied.exception.code)
                    with urlopen(Request(url, data=b"", headers={"Authorization": "Bearer token"}), timeout=3) as result:
                        self.assertEqual(before, json.load(result)["cleared_through"])
                finally:
                    server.shutdown()
                    worker.join()
            self.assertEqual([], history.page(None)["entries"])
            self.assertEqual([], list(study.events))
            self.assertTrue(study.pending)
            study.record("새 기록")
            self.assertGreater(history.page(None)["entries"][0]["id"], before)

    @unittest.skipIf(cv2 is None, "OpenCV unavailable")
    def test_keeps_a_textured_tablet_clipped_at_the_side(self):
        image = Image.new("RGB", (600, 800), (101, 101, 101))
        draw = ImageDraw.Draw(image)
        draw.rectangle((15, 18, 483, 656), fill=(236, 236, 236))
        for y in range(38, 637, 17):
            for x in range(45, 463, 22):
                draw.rectangle((x,y,x+10,y+4),fill=(30,30,30))
        draw.polygon([(481,210),(599,177),(599,565),(499,512)],fill=(151,169,240))
        for y in range(230, 512, 12):
            for x in range(507, 598, 13):
                draw.rectangle((x,y,x+6,y+2),fill=(50,55,90))
        x0, _, x1, _ = document_region(image)
        self.assertGreater(x0, 440)
        self.assertEqual(x1, 600)

    def test_nearby_gap_only_and_explicit_end(self):
        study = Study(None, 1, True)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.detected_questions = {87}
        self.assertEqual((set(), {87}, set()), study.coverage_numbers())
        study.detected_questions = {1, 3, 4}
        self.assertEqual({2}, study.coverage_numbers()[2])
        study.expected_range = (1, 6)
        self.assertEqual({2, 5, 6}, study.coverage_numbers()[2])

    def test_same_number_in_different_subjects_is_not_merged(self):
        q = QuestionView(False, "sameprintedwords")
        old = FrameView(1, False, {2: q}, subject="한국사")
        new = FrameView(1, False, {2: q}, subject="수학")
        self.assertFalse(same_page(old, new))
        study = Study(None, 1, False)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        study.stream = "run"
        study.update_scope(old, 10)
        study.page_scopes[1] = ("한국사", "")
        study.detected_questions = {2}
        study.player.save("책", (1,), 2, 1)
        study.update_scope(new, 11)
        study.page_scopes[2] = ("수학", "")
        study.player.save("책", (2,), 2, 4)
        study.last_routed_page = 2
        study.player.observe("책", 2, 12)
        from unittest.mock import patch

        with patch('phone_server.time.monotonic', side_effect=(100, 115, 117)):
            first = study.poll("run", None, False, draining=True)["packet"]
            study.poll("run", first["id"], True, draining=True)
            second = study.poll("run", None, False, draining=True)["packet"]
        self.assertEqual((2, 1, "한국사"), (first["question"], first["answer"], first["subject"]))
        self.assertEqual((2, 4, "수학"), (second["question"], second["answer"], second["subject"]))

    def test_photo_cursor_beyond_thirty_and_archive_budget(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            compact = PhotoArchive(path, max_bytes=12, min_free=0)
            important = compact.retain("run", b"12345", return_name=True)
            weak = compact.retain("run", b"23456", return_name=True, important=False)
            compact.retain("run", b"34567")
            self.assertTrue((path / important).exists())
            self.assertFalse((path / weak).exists())
            self.assertEqual(10, compact.info()["bytes"])
            for i in range(67):
                (path / f"20261116_150000_{i:06d}_{i:032x}.jpg").write_bytes(b"test")
            study = Study(None, 1, True)
            self.addCleanup(study.pool.shutdown)
            self.addCleanup(study.routing_pool.shutdown)
            with create_server("127.0.0.1", 0, "token", study, path) as server:
                worker = threading.Thread(target=server.serve_forever, daemon=True)
                worker.start()
                base = f"http://127.0.0.1:{server.server_port}/photos"
                try:
                    received = []
                    cursor = None
                    for _ in range(4):
                        url = base if not cursor else base + "?before=" + cursor
                        with urlopen(Request(url, headers={"Authorization": "Bearer token"}), timeout=3) as response:
                            data = json.load(response)
                        received.extend(data["photos"])
                        cursor = data["next_before"]
                        if not cursor:
                            break
                    self.assertEqual(69, len(received))
                    self.assertEqual(received, sorted(set(received), reverse=True))
                finally:
                    server.shutdown()
                    worker.join()

    def test_toeic_audio_requires_matching_printed_text(self):
        anchors = {32: 'whendoesthelibraryopen', 33: 'wherewillthespeakersmeet', 34: 'whatshouldthemanbring'}
        study = Study(None, 1, False, listening_questions=anchors, listening_anchors=anchors)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        good = FrameView(5, False, {q: QuestionView(False, text[:16]) for q, text in anchors.items()})
        self.assertTrue(study.recognize_listening_page(good))
        self.assertFalse(study.recognize_listening_page(FrameView(5, False, good.questions, subject="수학")))
        self.assertFalse(study.recognize_listening_page(FrameView(5, False, {32: good.questions[32]})))
        self.assertFalse(study.is_listening_question(5, 32))

    def test_newest_frame_reaches_local_preview_before_routing_finishes(self):
        from study_monitor import make_monitor_server
        with TemporaryDirectory() as directory:
            root = Path(directory)
            blocked = threading.Event()
            def route(stream, photo):
                blocked.wait(3)
                return None
            recorder = Recorder()
            recorder.recent = lambda: recorder.events
            study = Study(None, 1, False, router=route, monitor=recorder)
            html = root / "index.html"
            html.write_text("local", encoding="utf-8")
            photo = io.BytesIO()
            Image.new("RGB", (500, 300), "white").save(photo, format="JPEG")
            with create_server("127.0.0.1", 0, "token", study) as phone, make_monitor_server(
                0, recorder, root, html, study.monitor_state, study.previews
            ) as dashboard:
                for server in (phone, dashboard):
                    threading.Thread(target=server.serve_forever, daemon=True).start()
                try:
                    upload = Request(f"http://127.0.0.1:{phone.server_port}/frame", data=photo.getvalue(),
                                     headers={"Authorization":"Bearer token","X-Study-Session":"a"*36})
                    with urlopen(upload, timeout=3) as res:
                        self.assertEqual(200,res.status)
                    base = f"http://127.0.0.1:{dashboard.server_port}"
                    with urlopen(base+"/state", timeout=3) as res:
                        preview = json.load(res)["state"]["previews"][0]
                    self.assertTrue(study.route_pending)
                    self.assertEqual(1,preview["frame"])
                    with urlopen(base+"/live-photo/"+preview["id"], timeout=3) as res:
                        self.assertTrue(res.read().startswith(bytes([255,216])))
                finally:
                    blocked.set()
                    study.pool.shutdown()
                    study.routing_pool.shutdown()
                    phone.shutdown()
                    dashboard.shutdown()

    def test_parallel_route_merges_groups_in_capture_order(self):
        later_running = threading.Event()
        def one(stream, photo):
            if not later_running.wait(2):
                raise RuntimeError("parallel route never started")
            return FrameView(1, False, {})
        def batch(stream, photos):
            later_running.set()
            return (FrameView(2, False, {}), FrameView(3, False, {}))
        study = Study(None,1,False,router=one,batch_router=batch,parallel_routing=True)
        self.addCleanup(study.pool.shutdown)
        self.addCleanup(study.routing_pool.shutdown)
        self.addCleanup(study.route_assist.shutdown)
        order=[]
        study.route = lambda stream, group, photo, captured, **details: order.append((group,details["result"].printed))
        study.route_batch(tuple(("run",i,b"frame",float(i)) for i in (1,2,3)),boost=True)
        self.assertEqual([(1,1),(2,2),(3,3)],order)

    def test_listening_progress_names_clip_and_text(self):
        events = []
        windows = [QuestionWindow("7", Decimal(0), Decimal(1))]
        result = transcribe_questions([1, 2], windows, lambda clip: "Local audio", 2,
                                      progress=lambda stage, status, **data: events.append((stage, status, data)))
        self.assertEqual(result, {"questions": {"7": "Local audio"}})
        self.assertEqual([item[1] for item in events], ["running", "done"])
        self.assertEqual(events[-1][2]["question"], 7)
        self.assertEqual(events[-1][2]["transcript"], "Local audio")


if __name__ == "__main__":
    unittest.main()
