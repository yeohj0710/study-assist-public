"""Create a local English listening transcript manifest from timed question clips."""

import argparse
import csv
import json
import os
import re
import tempfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import ceil
from pathlib import Path
from uuid import uuid4

from study_monitor import TraceStore


SAMPLE_RATE = 16_000
WINDOW_FIELDS = {"question", "start", "end"}
CACHED_MODELS = ("small.en", "base.en", "small", "base", "turbo", "tiny.en", "tiny")


@dataclass(frozen=True)
class QuestionWindow:
    question: str
    start: Decimal
    end: Decimal


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON 항목 이름 {key!r}이 반복됩니다.")
        result[key] = value
    return result


def read_windows(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        if path.suffix.lower() == ".csv":
            try:
                reader = csv.DictReader(source, strict=True)
                if sorted(reader.fieldnames or ()) != sorted(WINDOW_FIELDS):
                    raise ValueError("CSV 첫 줄에 question,start,end 열이 필요합니다.")
                rows = list(reader)
            except csv.Error as exc:
                raise ValueError(f"CSV 행을 읽을 수 없습니다. {exc}") from exc
        elif path.suffix.lower() == ".json":
            rows = json.load(source, parse_float=Decimal, object_pairs_hook=unique_json_object)
        else:
            raise ValueError("구간 파일의 확장자는 .csv 또는 .json이어야 합니다.")

    if type(rows) is not list or not rows:
        raise ValueError("구간 파일에 문항을 한 개 이상 넣으세요.")

    windows = []
    seen = set()
    for index, row in enumerate(rows, 1):
        if type(row) is not dict or row.keys() != WINDOW_FIELDS:
            raise ValueError(f"구간 {index}에는 question, start, end 값만 넣으세요.")
        question = str(row["question"]).strip()
        if not re.fullmatch(r"[1-9][0-9]{0,2}", question):
            raise ValueError(f"구간 {index}의 문항 번호는 1부터 999까지 입력하세요.")
        if question in seen:
            raise ValueError(f"{question}번 문항의 구간이 반복됩니다.")

        try:
            start = Decimal(str(row["start"]).strip())
            end = Decimal(str(row["end"]).strip())
        except InvalidOperation as exc:
            raise ValueError(f"{question}번 문항의 시작과 끝을 초 단위 숫자로 입력하세요.") from exc
        if not (start.is_finite() and end.is_finite() and 0 <= start < end):
            raise ValueError(f"{question}번 문항은 0초 이후에 시작하고 시작 시각보다 늦게 끝나야 합니다.")

        seen.add(question)
        windows.append(QuestionWindow(question, start, end))
    return windows


def transcribe_questions(audio, windows, transcribe, sample_rate=SAMPLE_RATE, *, progress=None):
    duration = Decimal(len(audio)) / sample_rate
    clips = []
    for window in windows:
        if window.end > duration:
            raise ValueError(f"{window.question}번 문항의 끝 {window.end}초가 음원 길이 {duration}초를 넘습니다.")
        first_sample = ceil(window.start * sample_rate)
        end_sample = ceil(window.end * sample_rate)
        if first_sample >= end_sample:
            raise ValueError(f"{window.question}번 문항의 구간이 너무 짧습니다.")
        clips.append((window.question, first_sample, end_sample))

    questions = {}
    transcripts = {}
    for question, first_sample, end_sample in clips:
        bounds = (first_sample, end_sample)
        clip = {"question": int(question), "start": first_sample / sample_rate, "end": end_sample / sample_rate}
        if progress:
            progress("listening", "running", **clip)
        if bounds not in transcripts:
            try:
                transcript = " ".join(transcribe(audio[first_sample:end_sample]).split())
                if not transcript:
                    raise ValueError(f"{question}번 문항에서 영어 음성을 인식하지 못했습니다. 음원과 구간을 확인하세요.")
            except (OSError, ValueError, RuntimeError, ImportError) as error:
                if progress:
                    progress("listening", "error", **clip, message=type(error).__name__)
                raise
            transcripts[bounds] = transcript
        questions[question] = transcripts[bounds]
        if progress:
            progress("listening", "done", **clip, transcript=questions[question][:16000])
    return {"questions": questions}


def decode_local_audio(path):
    import av
    import numpy as np

    resampler = av.AudioResampler(format="fltp", layout="mono", rate=SAMPLE_RATE)
    chunks = []
    try:
        with path.open("rb") as source, av.open(source, mode="r") as container:
            if not container.streams.audio:
                raise ValueError(f"음원에 오디오 트랙이 없습니다. {path}")
            for frame in container.decode(audio=0):
                frame.pts = None
                chunks.extend(part.to_ndarray().ravel() for part in resampler.resample(frame))
            if chunks:
                chunks.extend(part.to_ndarray().ravel() for part in resampler.resample(None))
    except av.error.FFmpegError as exc:
        raise ValueError(f"음원에서 오디오를 읽을 수 없습니다. {path}") from exc
    if not chunks:
        raise ValueError(f"음원에서 오디오를 읽을 수 없습니다. {path}")
    return np.concatenate(chunks)

def load_whisper(model_name):
    from faster_whisper import WhisperModel
    from faster_whisper.utils import download_model
    from huggingface_hub.errors import LocalEntryNotFoundError

    candidates = (model_name,) if model_name else CACHED_MODELS
    for candidate in candidates:
        model_path = Path(candidate).expanduser()
        if not (model_name and model_path.is_dir()):
            try:
                model_path = Path(download_model(candidate, local_files_only=True, use_auth_token=False))
            except LocalEntryNotFoundError:
                continue
        # Faster Whisper otherwise fetches a tokenizer if it is missing.
        missing = [
            name for name in ("model.bin", "config.json", "tokenizer.json")
            if not (model_path / name).is_file()
        ]
        if not missing:
            return WhisperModel(str(model_path), device="cpu", compute_type="int8", local_files_only=True)
        if model_name:
            raise ValueError(f"로컬 Whisper 모델에 필요한 파일이 없습니다. {', '.join(missing)}")

    raise ValueError("캐시에서 Whisper 모델을 찾지 못했습니다. --model에 로컬 모델 폴더나 캐시된 모델 이름을 입력하세요.")


def write_manifest(path, manifest):
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        pending = Path(handle.name)
    try:
        with pending.open("w", encoding="utf-8", newline="\n") as output:
            json.dump(manifest, output, ensure_ascii=False, allow_nan=False, indent=2)
            output.write("\n")

        # Publish the complete document atomically and fail if the destination already exists.
        if os.name == "nt":
            pending.rename(path)
        else:
            os.link(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="로컬 영어 연습 음원을 문항별 자막 JSON으로 변환합니다.",
        epilog='CSV 열 이름은 question,start,end입니다. JSON 예시는 [{"question":7,"start":1.5,"end":8}]입니다. 구간은 초 단위입니다.',
    )
    parser.add_argument("--audio", type=Path, required=True, help="영어 연습 음원 파일")
    parser.add_argument("--windows", type=Path, required=True, help="문항별 시작과 끝을 적은 CSV 또는 JSON 파일")
    parser.add_argument("--output", type=Path, required=True, help="새 자막 JSON 파일")
    parser.add_argument("--model", help="로컬 Whisper 모델 폴더 또는 캐시된 모델 이름")
    args = parser.parse_args(argv)
    trace = TraceStore(Path(__file__).resolve().parent / "study-monitor.sqlite3")
    run = uuid4().hex[:12]

    def progress(stage, status, **fields):
        trace.emit(stage, status, run=run, provider="local", model="Whisper",
                   source=args.audio.name, **fields)

    try:
        if args.output.exists():
            raise FileExistsError(f"출력 파일이 이미 있습니다. 새 경로를 입력하세요. {args.output}")
        windows = read_windows(args.windows)

        progress("listening", "decoding")
        audio = decode_local_audio(args.audio)

        model = None

        def transcribe(clip):
            nonlocal model
            if model is None:
                model = load_whisper(args.model)
            segments, _info = model.transcribe(
                clip, language="en", temperature=0, condition_on_previous_text=False, vad_filter=True
            )
            return " ".join(segment.text for segment in segments)

        manifest = transcribe_questions(audio, windows, transcribe, progress=progress)
        write_manifest(args.output, manifest)
        progress("listening", "saved", questions=list(map(int, manifest["questions"])), message=args.output.name)
    except ImportError as exc:
        progress("listening", "error", message=type(exc).__name__)
        parser.error(f"faster-whisper와 오디오 처리 라이브러리를 불러오지 못했습니다. {exc}")
    except (OSError, ValueError, RuntimeError) as exc:
        progress("listening", "error", message=type(exc).__name__)
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())