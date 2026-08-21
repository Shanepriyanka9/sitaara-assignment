"""
Video & Subtitle Automated QC Skill
===================================
Automated quality control for video exports and subtitle files.
"""
import argparse
import datetime
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
WHISPER_MODEL = "base"
MAX_SEGMENT_WER_PASS = 0.35
MAX_GLOBAL_WER_PASS = 0.25
MIN_SRT_DURATION_SEC = 0.3
SUPPORTED_EXTS = {".mp4", ".mov", ".mkv", ".webm"}


def normalize_text(text: str) -> str:
    """Strip HTML tags, punctuation, and normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", text)  # Strip HTML tags like <b>, <i>
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def find_subtitle_file(video_path: Path, search_root: Path) -> Optional[Path]:
    """Locate corresponding .srt file via sidecar, sibling folders, or recursive lookup."""
    sidecar = video_path.with_suffix(".srt")
    if sidecar.exists():
        return sidecar

    stem_lower = video_path.stem.lower()

    possible_sub_dirs = [
        video_path.parent / "Subtitles",
        video_path.parent / "subtitles",
        video_path.parent.parent / "Subtitles",
        video_path.parent.parent / "subtitles",
        search_root / "Subtitles",
        search_root / "subtitles",
    ]

    for sub_dir in possible_sub_dirs:
        if sub_dir.exists() and sub_dir.is_dir():
            for srt_file in sub_dir.iterdir():
                if srt_file.is_file() and srt_file.suffix.lower() == ".srt":
                    if srt_file.stem.lower() == stem_lower:
                        return srt_file

    for srt_file in search_root.rglob("*.srt"):
        if srt_file.is_file() and srt_file.stem.lower() == stem_lower:
            return srt_file

    return None


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
        res = subprocess.run(command, capture_output=True, text=True, check=True)
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
    srt_path: Optional[Path], video_duration: Optional[float] = None
) -> Tuple[List[srt.Subtitle], List[dict]]:
    """Parse SRT file, check structural issues, and normalize timeline offset drift."""
    if srt_path is None or not srt_path.exists():
        return [], [{"type": "INVALID_SRT", "detail": "Subtitle file is missing."}]

    if srt_path.stat().st_size == 0:
        return [], [{"type": "INVALID_SRT", "detail": "Subtitle file is empty (0 bytes)."}]

    try:
        with open(srt_path, "r", encoding="utf-8-sig") as f:
            content = f.read().strip()
            if not content:
                return [], [{"type": "INVALID_SRT", "detail": "Subtitle file is empty."}]
            subtitles = list(srt.parse(content))
    except Exception as e:
        return [], [{"type": "INVALID_SRT", "detail": f"Malformed SRT syntax: {str(e)}"}]

    if not subtitles:
        return [], [{"type": "INVALID_SRT", "detail": "No valid subtitle entries found."}]

    defects = []

    # Check for timeline-wide export offset (e.g., master timeline timecodes)
    first_start = subtitles[0].start.total_seconds()
    if video_duration and first_start > video_duration:
        offset_td = subtitles[0].start
        defects.append({
            "type": "TIMELINE_OFFSET",
            "detail": f"Subtitles start at {first_start:.2f}s on a {video_duration:.2f}s clip (Master timeline offset of ~{first_start:.2f}s detected).",
            "suggested_fix": f"Shift all subtitle timecodes by -{first_start:.2f}s to align with clip start."
        })
        # Shift subtitles to 0 for audio/text alignment evaluation
        aligned_subs = []
        for s in subtitles:
            aligned_subs.append(
                srt.Subtitle(
                    index=s.index,
                    start=max(datetime.timedelta(0), s.start - offset_td),
                    end=max(datetime.timedelta(0), s.end - offset_td),
                    content=s.content,
                )
            )
        subtitles = aligned_subs
    
    for i, sub in enumerate(subtitles):
        start_sec = sub.start.total_seconds()
        end_sec = sub.end.total_seconds()

        if end_sec <= start_sec:
            defects.append({
                "type": "SRT_SYNTAX",
                "detail": f"Subtitle #{sub.index}: End time ({end_sec:.2f}s) <= start time ({start_sec:.2f}s)."
            })

        if (end_sec - start_sec) < MIN_SRT_DURATION_SEC:
            defects.append({
                "type": "SRT_SYNTAX",
                "detail": f"Subtitle #{sub.index}: Extremely short duration ({(end_sec - start_sec):.2f}s)."
            })

        if video_duration and start_sec > video_duration:
            defects.append({
                "type": "SRT_SYNTAX",
                "detail": f"Subtitle #{sub.index}: Subtitle starts ({start_sec:.2f}s) after video ends ({video_duration:.2f}s)."
            })

        if i > 0:
            prev_end = subtitles[i - 1].end.total_seconds()
            if start_sec < prev_end:
                defects.append({
                    "type": "SRT_SYNTAX",
                    "detail": f"Subtitle #{sub.index} overlaps with Subtitle #{subtitles[i - 1].index}."
                })

    return subtitles, defects


def run_segment_qc(
    whisper_segments: list, srt_subtitles: list
) -> Tuple[List[dict], float]:
    """Compare Whisper transcribed words with SRT subtitle blocks using normalized text."""
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
        sub_text_clean = normalize_text(sub.content)

        if not sub_text_clean:
            continue

        words_in_window = [
            w for w in all_words
            if sub_start <= ((w.start + w.end) / 2.0) <= sub_end
        ]

        if not words_in_window:
            defects.append({
                "type": "TIMING_DRIFT" if all_words else "NO_SPEECH_DETECTED",
                "timestamp": f"{sub.start} --> {sub.end}",
                "detail": f"No spoken speech detected inside window ({sub_start:.2f}s - {sub_end:.2f}s).",
                "subtitle_text": sub.content.strip(),
                "spoken_text": "[SILENCE / DRIFT]",
            })
            continue

        spoken_text = " ".join(w.word.strip() for w in words_in_window)
        norm_spoken = normalize_text(spoken_text)
        seg_wer = wer(sub_text_clean, norm_spoken) if sub_text_clean else 1.0

        if seg_wer > MAX_SEGMENT_WER_PASS:
            defects.append({
                "type": "TEXT_MISMATCH",
                "timestamp": f"{sub.start} --> {sub.end}",
                "detail": f"Segment text discrepancy ({seg_wer * 100:.1f}% mismatch).",
                "subtitle_text": sub.content.strip(),
                "spoken_text": spoken_text,
            })

    return defects, global_wer


def process_video_qc(
    model: WhisperModel, video_path: Path, root_search_dir: Path
) -> dict:
    print(f"\n--> Inspecting: {video_path.parent.name}/{video_path.name}")
    srt_path = find_subtitle_file(video_path, root_search_dir)

    is_valid, probe_data, probe_msg = probe_media(video_path)
    if not is_valid:
        return {
            "file": video_path.name,
            "folder": video_path.parent.name,
            "status": "FAIL",
            "reason": probe_msg,
            "defects": [{"type": "FILE_CORRUPT", "detail": probe_msg}],
            "metrics": {},
        }

    video_duration = float(probe_data.get("format", {}).get("duration", 0.0))

    subtitles, structural_defects = parse_and_validate_srt(
        srt_path, video_duration
    )
    if any(d["type"] == "INVALID_SRT" for d in structural_defects):
        return {
            "file": video_path.name,
            "folder": video_path.parent.name,
            "status": "FAIL",
            "reason": structural_defects[0]["detail"],
            "defects": structural_defects,
            "metrics": {},
        }

    try:
        segments, info = model.transcribe(
            str(video_path), vad_filter=True, word_timestamps=True
        )
        whisper_segments = list(segments)
    except Exception as e:
        return {
            "file": video_path.name,
            "folder": video_path.parent.name,
            "status": "FAIL",
            "reason": f"Whisper transcription failed: {str(e)}",
            "defects": [{"type": "TRANSCRIPTION_ERROR", "detail": str(e)}],
            "metrics": {},
        }

    segment_defects, global_wer = run_segment_qc(whisper_segments, subtitles)
    all_defects = structural_defects + segment_defects

    # Determine final QC status
    has_critical = any(d["type"] in ["FILE_CORRUPT", "INVALID_SRT"] for d in all_defects)
    has_offset = any(d["type"] == "TIMELINE_OFFSET" for d in all_defects)
    text_mismatches = [d for d in all_defects if d["type"] == "TEXT_MISMATCH"]

    if has_critical:
        status = "FAIL"
    elif has_offset:
        # Flag as NEEDS_REVIEW so editors know to apply the timestamp offset
        status = "NEEDS_REVIEW" if len(text_mismatches) < 3 else "FAIL"
    elif len(text_mismatches) > 4 or global_wer > 0.40:
        status = "FAIL"
    elif all_defects:
        status = "NEEDS_REVIEW"
    else:
        status = "PASS"

    return {
        "file": video_path.name,
        "folder": video_path.parent.name,
        "srt_file": srt_path.name if srt_path else None,
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
    md += f"**Summary:** Total Deliverables: {len(results)} | ✅ PASS: {pass_count} | ⚠️ NEEDS REVIEW: {review_count} | ❌ FAIL: {fail_count}\n\n"

    md += "## Overview Table\n\n"
    md += "| File | Folder | Subtitle | Status | Global WER | Defects Found |\n"
    md += "| :--- | :--- | :--- | :---: | :---: | :---: |\n"
    for r in results:
        badge = "✅ PASS" if r["status"] == "PASS" else ("⚠️ REVIEW" if r["status"] == "NEEDS_REVIEW" else "❌ FAIL")
        wer_str = f"{r['metrics'].get('global_wer', 0.0) * 100:.1f}%" if "global_wer" in r.get("metrics", {}) else "N/A"
        srt_name = r.get("srt_file") or "None"
        md += f"| `{r['file']}` | `{r.get('folder', 'root')}` | `{srt_name}` | {badge} | {wer_str} | {len(r['defects'])} |\n"

    md += "\n## Actionable Remediation Details\n\n"
    defective_reports = [r for r in results if r["defects"]]

    for r in defective_reports:
        md += f"### `{r['file']}` ({r.get('folder', 'root')}) — Status: {r['status']}\n"
        for d in r["defects"]:
            md += f"- **[{d['type']}]** {d['detail']}\n"
            if "suggested_fix" in d:
                md += f"  - *Action:* {d['suggested_fix']}\n"
            if "subtitle_text" in d and "spoken_text" in d:
                md += f"  - *Timestamp:* `{d.get('timestamp', 'N/A')}`\n"
                md += f'  - *Expected Subtitle:* "{d["subtitle_text"]}"\n'
                md += f'  - *Spoken Audio:* "{d["spoken_text"]}"\n'
        md += "\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)


def main():
    parser = argparse.ArgumentParser(description="Automated Video & Subtitle QC Skill")
    parser.add_argument("samples_dir", type=str, help="Directory containing video and .srt files")
    parser.add_argument("--output", type=str, default="./output", help="Directory to save reports")
    args = parser.parse_args()

    samples_dir = Path(args.samples_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading Whisper model '{WHISPER_MODEL}'...")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    video_files = [
        f for f in samples_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS and not f.name.startswith("._")
    ]

    if not video_files:
        print(f"No supported video files ({', '.join(sorted(SUPPORTED_EXTS))}) found in {samples_dir.resolve()}")
        return

    video_files.sort(
        key=lambda p: (
            p.parent.name,
            [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", p.name)],
        )
    )
    results = [process_video_qc(model, video, samples_dir) for video in video_files]
    generate_reports(results, output_dir)

    print("\n================================")
    print("QC SUMMARY")
    print("================================")
    for r in results:
        print(f"{r.get('folder', '')}/{r['file']:<28} -> {r['status']}")
    print(f"\nDetailed actionable reports written to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()