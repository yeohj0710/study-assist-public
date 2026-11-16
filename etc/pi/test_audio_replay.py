import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import book_session


class StudyFlowTests(unittest.TestCase):
    def test_solver_attaches_optional_audio_with_its_mime_type(self):
        with tempfile.TemporaryDirectory() as folder:
            clip = Path(folder) / 'track.wav'
            clip.write_bytes(b'RIFF\x00\x00\x00\x00WAVE')
            with patch.object(book_session, 'urlopen') as open_url:
                open_url.return_value.__enter__.return_value.read.return_value = (
                    '{"request_id":"r1","status":"ok","choice":3}')
                got = book_session.request_solver('https://example.invalid/solve',
                                                  '17', [], 'r1', audio=clip)
            self.assertEqual(got['choice'], 3)
            req = json.loads(open_url.call_args.args[0].data)
            self.assertEqual(req['audio']['mime_type'], 'audio/wav')
            self.assertEqual(req['audio']['base64'], 'UklGRgAAAABXQVZF')

    def test_revisit_replays_page_answers_and_suppresses_other_page(self):
        from page_replay import PageReplay
        replay = PageReplay()
        replay.observe('교재', 42, 0)
        replay.observe('교재', 42, 3)
        replay.save('교재', (42,), 18, 4)
        replay.save('교재', (42, 43), 17, 3)
        self.assertEqual(replay.next_answer(3), (18, 4))
        replay.finished(6)
        replay.observe(None, None, 6)
        self.assertIsNone(replay.next_answer(6))
        replay.observe('교재', 44, 9)
        replay.observe('교재', 44, 12)
        self.assertIsNone(replay.next_answer(12))
        replay.observe('교재', 42, 15)
        self.assertIsNone(replay.next_answer(15))
        replay.observe('교재', 42, 18)
        self.assertEqual(replay.next_answer(18), (17, 3))
        self.assertIsNone(replay.next_answer(19))
        replay.finished(21)
        self.assertEqual(replay.next_answer(21), (18, 4))
        replay.finished(24)
        for second in range(21, 40, 3):
            replay.observe('교재', 42, second)
        self.assertEqual(replay.next_answer(39), (17, 3))
