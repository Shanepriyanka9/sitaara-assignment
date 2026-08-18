# Video & Subtitle Automated QC Skill

A self-contained CLI tool and AI assistant skill that automates quality control for batches of short-form video exports and corresponding `.srt` subtitle files.

---

## When to Use This Skill
Run this tool at the end of a video editing sprint before publishing or archiving footage to ensure that:
1. Video files are uncorrupted and contain readable audio/video streams.
2. Subtitle files exist, have valid formatting, and do not overlap.
3. Subtitle text accurately reflects the spoken audio with zero audible desynchronization.

---

## Prerequisites & Installation

### 1. System Dependencies
Ensure `ffmpeg` / `ffprobe` is installed and available in your system `PATH`:
- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt update && sudo apt install -y ffmpeg`
- **Windows**: Install via `winget install Gyan.FFmpeg` or download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add to `PATH`.

### 2. Python Dependencies
Python 3.10+ is recommended. Install required packages:
```bash
pip install -r requirements.txt