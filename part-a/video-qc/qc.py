import argparse
import json
import re
import subprocess
from pathlib import Path

import srt
from faster_whisper import WhisperModel
from jiwer import wer

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

WHISPER_MODEL = "tiny"
MAX_WER_PASS = 0.20
MAX_WER_REVIEW = 0.40
MAX_TIMING_DIFF_SECONDS = 2.0


# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normalize text before comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def run_ffprobe(video_path: Path) -> dict:
    """Check whether the video is readable and collect basic metadata."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-print_format", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception as e:
        return {"error": str(e)}


def load_srt(srt_path: Path):
    """Load and parse SRT subtitle entries."""
    with open(srt_path, "r", encoding="utf-8-sig") as f:
        return list(srt.parse(f.read()))


def process_video(model: WhisperModel, video_path: Path, srt_path: Path) -> dict:
    print(f"\n--> Running QC on: {video_path.name}")
    probe_data = run_ffprobe(video_path)

    # 1. Transcribe
    segments, _ = model.transcribe(str(video_path), vad_filter=True)
    whisper_segments = list(segments)
    whisper_full_text = " ".join(s.text.strip() for s in whisper_segments)

    # 2. Parse SRT
    srt_segments = load_srt(srt_path)
    srt_full_text = " ".join(s.content.strip() for s in srt_segments)

    # 3. Text Comparison
    norm_whisper = normalize_text(whisper_full_text)
    norm_srt = normalize_text(srt_full_text)

    wer_score = wer(norm_srt, norm_whisper) if norm_srt else 1.0

    # 4. Timing Check
    first_whisper_start = whisper_segments[0].start if whisper_segments else 0.0
    first_srt_start = srt_segments[0].start.total_seconds() if srt_segments else 0.0
    start_timing_diff = abs(first_whisper_start - first_srt_start)

    # Status classification
    if wer_score <= MAX_WER_PASS and start_timing_diff <= MAX_TIMING_DIFF_SECONDS:
        result_status = "PASS"
    elif wer_score <= MAX_WER_REVIEW:
        result_status = "NEEDS_REVIEW"
    else:
        result_status = "FAIL"

    return {
        "file": video_path.name,
        "srt_file": srt_path.name,
        "result": result_status,
        "metrics": {
            "wer": round(wer_score, 4),
            "start_timing_diff_sec": round(start_timing_diff, 2),
        },
        "streams_found": len(probe_data.get("streams", []))
    }


def create_markdown_report(results: list) -> str:
    md = "# Video Subtitle QC Report\n\n"
    md += "| Video File | Status | WER | Start Offset Diff |\n"
    md += "| :--- | :--- | :--- | :--- |\n"
    for r in results:
        status_icon = "✅ PASS" if r["result"] == "PASS" else ("⚠️ REVIEW" if r["result"] == "NEEDS_REVIEW" else "❌ FAIL")
        md += f"| {r['file']} | {status_icon} | {r['metrics']['wer'] * 100:.1f}% | {r['metrics']['start_timing_diff_sec']}s |\n"
    return md


def main():
    parser = argparse.ArgumentParser(description="Subtitle Quality Control Script")
    parser.add_argument("samples_dir", type=str, help="Path to samples folder")
    parser.add_argument("--output", type=str, default="./output", help="Path to output folder")
    args = parser.parse_args()

    samples_folder = Path(args.samples_dir)
    output_folder = Path(args.output)
    output_folder.mkdir(parents=True, exist_ok=True)

    print(f"Loading Whisper model '{WHISPER_MODEL}'...")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    results = []
    video_files = list(samples_folder.glob("*.mp4"))

    if not video_files:
        print(f"No .mp4 files found in {samples_folder.resolve()}")
        return

    for video in video_files:
        srt_file = video.with_suffix(".srt")
        if not srt_file.exists():
            print(f"Skipping {video.name} (no matching .srt found)")
            continue

        result = process_video(model, video, srt_file)
        results.append(result)

    # Write JSON report
    json_path = output_folder / "report.json"
    with open(json_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=2)

    # Write Markdown report
    markdown = create_markdown_report(results)
    markdown_path = output_folder / "report.md"
    with open(markdown_path, "w", encoding="utf-8") as file:
        file.write(markdown)

    print("\n================================")
    print("QC COMPLETE")
    print("================================")
    for result in results:
        print(f"{result['file']}: {result['result']}")

    print(f"\nReports written to: {output_folder.resolve()}")


if __name__ == "__main__":
    main()