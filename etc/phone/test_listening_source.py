import importlib.util
import struct
import tempfile
import unittest
import wave
from decimal import Decimal
from pathlib import Path

import listening_source


class ListeningSourceTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.folder = Path(scratch.name)

    def windows(self, content, extension=".json"):
        path = self.folder / ("windows" + extension)
        path.write_text(content, encoding="utf-8")
        return listening_source.read_windows(path)

    def test_reads_numbered_windows_and_allows_shared_passages(self):
        expected = [
            listening_source.QuestionWindow("7", Decimal("1.5"), Decimal("8")),
            listening_source.QuestionWindow("8", Decimal("1.5"), Decimal("8")),
        ]
        self.assertEqual(expected, self.windows(
            '[{"question":7,"start":1.5,"end":8},{"question":"8","start":1.5,"end":8}]'
        ))
        self.assertEqual(expected, self.windows(
            "\ufeffquestion,start,end\n7,1.5,8\n8,1.5,8\n", ".csv"
        ))

    def test_rejects_invalid_json_windows(self):
        invalid = [
            "[]",
            '[{"question":1,"start":0,"end":1},{"question":"1","start":1,"end":2}]',
            '[{"question":1,"question":2,"start":0,"end":1}]',
            '[{"question":true,"start":0,"end":1}]',
            '[{"question":"01","start":0,"end":1}]',
            '[{"question":1000,"start":0,"end":1}]',
            '[{"question":1,"start":false,"end":1}]',
            '[{"question":1,"start":-1,"end":1}]',
            '[{"question":1,"start":1,"end":1}]',
            '[{"question":1,"start":0,"end":NaN}]',
            '[{"question":1,"start":0,"end":1,"extra":0}]',
        ]
        for document in invalid:
            with self.subTest(document=document), self.assertRaises(ValueError):
                self.windows(document)

    def test_rejects_invalid_csv_columns_and_rows(self):
        for document in (
            "question,start,start\n7,0,1\n",
            "question,start,end\n7,0\n",
            "question,start,end\n7,0,1,2\n",
            'question,start,end\n7,"0,1\n',
        ):
            with self.subTest(document=document), self.assertRaises(ValueError):
                self.windows(document, ".csv")

    def test_clips_samples_by_window_and_reuses_shared_passage_transcript(self):
        windows = self.windows(
            '[{"question":7,"start":0.24,"end":0.75},'
            '{"question":8,"start":0.24,"end":0.75},'
            '{"question":9,"start":0.75,"end":1}]'
        )
        seen = []

        def transcribe(samples):
            seen.append(samples)
            return "  Here is the   train. \n"

        manifest = listening_source.transcribe_questions(range(4), windows, transcribe, sample_rate=4)
        self.assertEqual([range(1, 3), range(3, 4)], seen)
        self.assertEqual({"questions": {key: "Here is the train." for key in ("7", "8", "9")}}, manifest)

    def test_rejects_out_of_range_and_subsample_windows_before_transcription(self):
        for start, end in (("0.75", "1.25"), ("0.01", "0.02")):
            with self.subTest(start=start, end=end):
                windows = self.windows(
                    f'[{{"question":7,"start":0,"end":0.5}},'
                    f'{{"question":8,"start":{start},"end":{end}}}]'
                )
                with self.assertRaisesRegex(ValueError, "8"):
                    listening_source.transcribe_questions(
                        range(4), windows, lambda _clip: self.fail("Transcribed an invalid input"), sample_rate=4
                    )

    def test_rejects_empty_transcript(self):
        windows = self.windows('[{"question":7,"start":0,"end":1}]')
        with self.assertRaisesRegex(ValueError, "7"):
            listening_source.transcribe_questions(range(4), windows, lambda _clip: " ", sample_rate=4)

    def test_writes_utf8_without_replacing_existing_manifest(self):
        output = self.folder / "practice.json"
        manifest = {"questions": {"7": "Café opens soon."}}
        listening_source.write_manifest(output, manifest)
        original = output.read_bytes()
        self.assertIn("Café".encode("utf-8"), original)
        self.assertTrue(original.startswith(b"{"))
        with self.assertRaises(FileExistsError):
            listening_source.write_manifest(output, {"questions": {"8": "Unrelated."}})
        self.assertEqual(original, output.read_bytes())

    @unittest.skipUnless(importlib.util.find_spec("av") and importlib.util.find_spec("numpy"),
                         "PyAV and NumPy are required for decoding")
    def test_decodes_local_pcm_to_mono_float32_at_16000_hz(self):
        path = self.folder / "practice.wav"
        with wave.open(str(path), "wb") as audio:
            audio.setparams((2, 2, 22_050, 0, "NONE", "not compressed"))
            audio.writeframes(struct.pack("<hh", 8192, 8192) * 22_050)

        samples = listening_source.decode_local_audio(path)
        self.assertEqual((16_000,), samples.shape)
        self.assertEqual("float32", samples.dtype.name)
        self.assertTrue(0.1 < samples[8000] < 0.5)
