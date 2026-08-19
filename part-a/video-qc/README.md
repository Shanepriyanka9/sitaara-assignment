# Video & Subtitle Automated QC Skill (`part-a/video-qc`)

A self-contained CLI tool and AI assistant skill that performs deterministic quality control on batches of video deliverables (`.mp4`, `.mov`, `.mkv`, `.webm`) and their associated `.srt` subtitle sidecars.

---

## 1. Skill Context & Invocation

* **Skill Location:** `part-a/video-qc` (Core engine: `qc.py`)
* **When to Run:** Execute this tool at the end of a video editing sprint before publishing, archiving, or handing off footage to ensure:

  * Video containers are uncorrupted and contain readable audio and video streams.
  * Subtitle files exist, are non-empty, and contain valid timecode structures without overlapping cues.
  * Subtitle cues do not exhibit timing drift or appear over extended silence.
  * Subtitle text accurately reflects spoken audio dialogue with zero script hallucination or omission.

---

## 2. Prerequisites & Environment Setup

### System Binaries

`ffmpeg` and `ffprobe` must be installed and available on your system's `PATH`.

* **macOS:**

  ```bash
  brew install ffmpeg
  ```

* **Ubuntu/Debian:**

  ```bash
  sudo apt update && sudo apt install -y ffmpeg
  ```

* **Windows:**

  ```bash
  winget install Gyan.FFmpeg
  ```

  or

  ```bash
  choco install ffmpeg
  ```

### Python Setup (No Cloud Keys Required)

This skill runs local, quantized CPU speech-to-text inference via `faster-whisper` (`int8`).

**No OpenAI, Google Cloud, or third-party API keys or environment variables are needed.**

```bash
# Navigate to skill directory
cd part-a/video-qc

# Create and activate a clean virtual environment
python -m venv .venv

# On Linux/macOS
source .venv/bin/activate

# On Windows (Command Prompt)
.venv\Scripts\activate

# Install pinned dependencies
pip install -r requirements.txt
```

---

## 3. How to Run

The skill requires one positional argument pointing to the folder containing your media, plus an optional `--output` flag for target reporting.

### CLI Syntax

```bash
python qc.py <PATH_TO_FOLDER> [--output <OUTPUT_DIRECTORY>]
```

### Execution Examples

**From inside `part-a/video-qc/`:**

```bash
# Run against the test samples folder
python qc.py ./samples

# Run against an absolute folder path on macOS/Linux
python qc.py /Users/evaluator/Desktop/sprint_deliverables

# Run against a Windows path with custom output target
python qc.py "C:\Production\Sprint_14" --output ./custom_output
```

**From the repository root:**

```bash
python part-a/video-qc/qc.py part-a/video-qc/samples --output part-a/video-qc/output
```

### Portability & Resilient Behavior

* **Zero Hard-Coded Paths:** Dynamically resolves all target folders and assets using standard `pathlib.Path`.
* **Multi-Format Container Parity:** Case-insensitively scans for `.mp4`, `.mov`, `.mkv`, and `.webm` files.
* **Empty / Invalid Directory Guard:** If the pointed folder contains no supported media, the script logs an informative message and exits cleanly without throwing an unhandled exception.

---

## 4. Defect Taxonomy & Evaluation Logic

Every video export is evaluated against deterministic thresholds configured in `qc.py`.

* **`[FILE_CORRUPT]` (❌ FAIL):** Missing video/audio stream or unreadable container via `ffprobe`.
* **`[INVALID_SRT]` (❌ FAIL):** `.srt` file is missing, empty (0 bytes), or contains invalid formatting.
* **`[SRT_SYNTAX]` (⚠️ REVIEW / FAIL):** End time <= start time, duration < 0.3s, start time exceeds video duration, or overlapping cues.
* **`[TIMING_DRIFT]` (⚠️ REVIEW):** Subtitle window contains no detected speech words (drift or silence).
* **`[NO_SPEECH_DETECTED]` (⚠️ REVIEW):** Subtitle exists over long stretches of complete silence.
* **`[TEXT_MISMATCH]` (❌ FAIL):** Word Error Rate (WER) between subtitle text and spoken dialogue > 35%.

### Status Resolution Rules

* **`PASS`:** Zero detected defects and global WER <= 20%.
* **`NEEDS_REVIEW`:** Non-critical warnings present (e.g., minor timing drift, short display durations) without severe structural failures.
* **`FAIL`:** File corruption, missing/empty `.srt`, segment text mismatches (> 35%), or global WER > 40%.

---

## 5. Output Deliverables & Actionable Remediation

All run deliverables are generated inside `./output` (or the directory passed via `--output`).

### `output/report.md` — Human-Actionable Summary

Contains:

* Overview table showing pass/fail status, global WER percentages, and defect counts.
* Detailed breakdown per failing file with exact timestamps, expected subtitle text, recognized audio transcription, and specific remediation advice for editors.

### `output/report.json` — Machine-Readable Payload

Contains a structured JSON object with:

* Full file metadata
* Parsed durations
* Quality metrics
* Defect lists

The JSON output can be used for ingestion by CI/CD pipelines, Slack alerts, or downstream agent workflows.
