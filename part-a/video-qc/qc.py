
"""
Video & Subtitle Automated QC Skill
===================================
Automated quality control for video exports and subtitle files.

Usage:
    python qc.py <PATH_TO_FOLDER>
    python qc.py ./samples
    python qc.py ./samples --output ./custom_output

Prerequisites:
    - ffmpeg / ffprobe installed and in PATH
    - pip install -r requirements.txt
"""
import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import srt
from faster_whisper import WhisperModel
from jiwer import wer

# ---------------------------------------------------------
# Threshold Configuration
# ---------------------------------------------------------
WHISPER_MODEL = "base"           # 'base' model for accurate word timestamps
MAX_SEGMENT_WER_PASS = 0.35      # 35% accommodates natural speech variations
MAX_TIMING_DRIFT_SECONDS = 1.5   # >1.5s flags timing drift
MIN_SRT_DURATION_SEC = 0.3       # Subtitles shorter than 300ms flag warning


def normalize_text(text: str) -> str:
    """Normalize text for reliable comparison."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def probe_media(video_path: Path) -> Tuple[bool, Optional[dict], str]:
    """Validate video integrity, container health, and audio streams using ffprobe."""
    command = [
        "ffprobe",
        "-v", "error",
        "-show_streams",
        "-show_format",
        "-print_format", "json",
        str(video_path),
    ]
    try:
        res = subprocess.run(
            command, capture_output=True, text=True, check=True
        )
        data = json.loads(res.stdout)

        streams = data.get("streams", [])
        has_video = any(s.get("codec_type") == "video" for s in streams)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        if not has_video:
            return False, data, "No video stream detected or file is corrupted."
        if not has_audio:
            return False, data, "Video has no audio stream to transcribe."

        return True, data, "Valid"
    except subprocess.CalledProcessError:
        return False, None, "Corrupt or unreadable video file."
    except Exception as e:
        return False, None, f"ffprobe error: {str(e)}"


def parse_and_validate_srt(
    srt_path: Path, video_duration: Optional[float] = None
) -> Tuple[List[srt.Subtitle], List[str]]:
    """Parse SRT file and flag structural/timestamp issues."""
    issues = []
    if not srt_path.exists():
        return [], ["Subtitle file is missing."]

    if srt_path.stat().st_size == 0:
        return [], ["Subtitle file is empty."]

    try:
        with open(srt_path, "r", encoding="utf-8-sig") as f:
            content = f.read().strip()
            if not content:
                return [], ["Subtitle file is empty."]
            subtitles = list(srt.parse(content))
    except Exception as e:
        return [], [f"Malformed SRT format: {str(e)}"]

    if not subtitles:
        return [], ["No valid subtitle entries found."]

    for i, sub in enumerate(subtitles):
        start_sec = sub.start.total_seconds()
        end_sec = sub.end.total_seconds()

        if end_sec <= start_sec:
            issues.append(
                f"Subtitle #{sub.index}: End time ({end_sec:.2f}s) is before or equal to start time ({start_sec:.2f}s)."
            )

        if (end_sec - start_sec) < MIN_SRT_DURATION_SEC:
            issues.append(
                f"Subtitle #{sub.index}: Extremely short duration ({(end_sec - start_sec):.2f}s)."
            )

        if video_duration and start_sec > video_duration:
            issues.append(
                f"Subtitle #{sub.index}: Subtitle starts ({start_sec:.2f}s) after video ends ({video_duration:.2f}s)."
            )

        if i > 0:
            prev_end = subtitles[i - 1].end.total_seconds()
            if start_sec < prev_end:
                issues.append(
                    f"Subtitle #{sub.index} overlaps with Subtitle #{subtitles[i - 1].index}."
                )

    return subtitles, issues


def run_segment_qc(
    whisper_segments: list, srt_subtitles: list
) -> Tuple[List[dict], float]:
    """Compare Whisper speech words with SRT subtitle blocks using word midpoint assignment."""
    defects = []

    all_words = []
    for s in whisper_segments:
        if s.words:
            all_words.extend(s.words)

    full_whisper_text = " ".join(s.text.strip() for s in whisper_segments)
    full_srt_text = " ".join(s.content.strip() for s in srt_subtitles)

    norm_w = normalize_text(full_whisper_text)
    norm_s = normalize_text(full_srt_text)
    global_wer = wer(norm_s, norm_w) if norm_s else 1.0

    for sub in srt_subtitles:
        sub_start = sub.start.total_seconds()
        sub_end = sub.end.total_seconds()
        sub_text = normalize_text(sub.content)

        # Word belongs to this subtitle if midpoint falls within the boundary
        words_in_window = [
            w for w in all_words
            if sub_start <= ((w.start + w.end) / 2.0) <= sub_end
        ]

        if not words_in_window:
            defects.append(
                {
                    "type": "TIMING_DRIFT" if all_words else "NO_SPEECH_DETECTED",
                    "timestamp": f"{sub.start} --> {sub.end}",
                    "detail": f"No speech detected inside window ({sub_start:.2f}s - {sub_end:.2f}s).",
                    "subtitle_text": sub.content.strip(),
                    "spoken_text": "[SILENCE / DRIFT]",
                }
            )
            continue

        spoken_text = " ".join(w.word.strip() for w in words_in_window)
        norm_spoken = normalize_text(spoken_text)
        seg_wer = wer(sub_text, norm_spoken) if sub_text else 1.0

        if seg_wer > MAX_SEGMENT_WER_PASS:
            defects.append(
                {
                    "type": "TEXT_MISMATCH",
                    "timestamp": f"{sub.start} --> {sub.end}",
                    "detail": f"Segment text discrepancy ({seg_wer * 100:.1f}% mismatch).",
                    "subtitle_text": sub.content.strip(),
                    "spoken_text": spoken_text,
                }
            )

    return defects, global_wer


def process_video_qc(
    model: WhisperModel, video_path: Path, samples_dir: Path
) -> dict:
    print(f"\n--> Inspecting: {video_path.name}")
    srt_path = video_path.with_suffix(".srt")

    is_valid, probe_data, probe_msg = probe_media(video_path)
    if not is_valid:
        return {
            "file": video_path.name,
            "status": "FAIL",
            "reason": probe_msg,
            "defects": [{"type": "FILE_CORRUPT", "detail": probe_msg}],
            "metrics": {},
        }

    video_duration = float(probe_data.get("format", {}).get("duration", 0.0))

    subtitles, srt_structural_issues = parse_and_validate_srt(
        srt_path, video_duration
    )
    if srt_structural_issues and not subtitles:
        return {
            "file": video_path.name,
            "status": "FAIL",
            "reason": srt_structural_issues[0],
            "defects": [
                {"type": "INVALID_SRT", "detail": err}
                for err in srt_structural_issues
            ],
            "metrics": {},
        }

    try:
        segments, _ = model.transcribe(
            str(video_path), vad_filter=True, word_timestamps=True
        )
        whisper_segments = list(segments)
    except Exception as e:
        return {
            "file": video_path.name,
            "status": "FAIL",
            "reason": f"Whisper transcription failed: {str(e)}",
            "defects": [{"type": "TRANSCRIPTION_ERROR", "detail": str(e)}],
            "metrics": {},
        }

    segment_defects, global_wer = run_segment_qc(whisper_segments, subtitles)
    all_defects = [
        {"type": "SRT_SYNTAX", "detail": issue}
        for issue in srt_structural_issues
    ] + segment_defects

    if not all_defects and global_wer <= 0.20:
        status = "PASS"
    elif (
        any(
            d["type"] in ["FILE_CORRUPT", "INVALID_SRT", "TEXT_MISMATCH"]
            for d in all_defects
        )
        or global_wer > 0.40
    ):
        status = "FAIL"
    else:
        status = "NEEDS_REVIEW"

    return {
        "file": video_path.name,
        "srt_file": srt_path.name if srt_path.exists() else None,
        "status": status,
        "metrics": {
            "global_wer": round(global_wer, 4),
            "video_duration_sec": round(video_duration, 2),
            "defect_count": len(all_defects),
        },
        "defects": all_defects,
    }


def generate_reports(results: List[dict], output_dir: Path):
    json_path = output_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    md_path = output_dir / "report.md"
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    review_count = sum(1 for r in results if r["status"] == "NEEDS_REVIEW")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")

    md = "# Video & Subtitle Batch QC Report\n\n"
    md += f"**Summary:** Total: {len(results)} | ✅ PASS: {pass_count} | ⚠️ NEEDS REVIEW: {review_count} | ❌ FAIL: {fail_count}\n\n"

    md += "## Overview\n\n"
    md += "| File | Status | Global WER | Defects Found |\n"
    md += "| :--- | :---: | :---: | :---: |\n"
    for r in results:
        badge = (
            "✅ PASS"
            if r["status"] == "PASS"
            else (
                "⚠️ REVIEW" if r["status"] == "NEEDS_REVIEW" else "❌ FAIL"
            )
        )
        wer_str = (
            f"{r['metrics'].get('global_wer', 0.0) * 100:.1f}%"
            if "global_wer" in r.get("metrics", {})
            else "N/A"
        )
        md += f"| `{r['file']}` | {badge} | {wer_str} | {len(r['defects'])} |\n"

    md += "\n## Actionable Defect Breakdown\n\n"
    defective_reports = [r for r in results if r["defects"]]

    if not defective_reports:
        md += (
            "✨ *All files passed quality checks with zero detected defects.*\n"
        )
    else:
        for r in defective_reports:
            md += f"### `{r['file']}` ({r['status']})\n"
            for d in r["defects"]:
                md += f"- **[{d['type']}]** {d['detail']}\n"
                if "subtitle_text" in d and "spoken_text" in d:
                    md += f"  - *Timestamp:* `{d.get('timestamp', 'N/A')}`\n"
                    md += f'  - *Subtitle:* "{d["subtitle_text"]}"\n'
                    md += f'  - *Spoken Audio:* "{d["spoken_text"]}"\n'
            md += "\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)


def main():
    parser = argparse.ArgumentParser(
        description="Automated Video & Subtitle QC Skill"
    )
    parser.add_argument(
        "samples_dir",
        type=str,
        help="Directory containing .mp4 and .srt files",
    )
    parser.add_argument(
        "--output", type=str, default="./output", help="Directory to save reports"
    )
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading Whisper model '{WHISPER_MODEL}'...")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    video_files = list(samples_dir.glob("*.mp4"))
    if not video_files:
        print(f"No .mp4 files found in {samples_dir.resolve()}")
        return

    results = [
        process_video_qc(model, video, samples_dir) for video in video_files
    ]
    generate_reports(results, output_dir)

    print("\n================================")
    print("QC SUMMARY")
    print("================================")
    for r in results:
        print(f"{r['file']:<20} -> {r['status']}")
    print(f"\nDetailed actionable reports written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()