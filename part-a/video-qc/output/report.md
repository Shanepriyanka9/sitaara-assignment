# Video & Subtitle Batch QC Report

**Summary:** Total: 8 | ✅ PASS: 2 | ⚠️ NEEDS REVIEW: 1 | ❌ FAIL: 5

## Overview

| File | Status | Global WER | Defects Found |
| :--- | :---: | :---: | :---: |
| `empty_subtitle.mp4` | ❌ FAIL | N/A | 1 |
| `good.mp4` | ✅ PASS | 0.0% | 0 |
| `missing_subtitle.mp4` | ❌ FAIL | N/A | 1 |
| `video1.mp4` | ✅ PASS | 0.0% | 0 |
| `video2.mp4` | ❌ FAIL | 100.0% | 1 |
| `video3.mp4` | ⚠️ REVIEW | 0.0% | 2 |
| `wrong_text.mp4` | ❌ FAIL | 450.0% | 2 |
| `wrong_timing.mp4` | ❌ FAIL | 317.6% | 2 |

## Actionable Defect Breakdown

### `empty_subtitle.mp4` (FAIL)
- **[INVALID_SRT]** Subtitle file is empty.

### `missing_subtitle.mp4` (FAIL)
- **[INVALID_SRT]** Subtitle file is missing.

### `video2.mp4` (FAIL)
- **[TEXT_MISMATCH]** Segment text discrepancy (100.0% mismatch).
  - *Timestamp:* `0:00:00.500000 --> 0:00:04.500000`
  - *Subtitle:* "This is a completely different recipe for baking chocolate cookies."
  - *Spoken Audio:* "to the Automated subtitle Quality Checking demo."

### `video3.mp4` (NEEDS_REVIEW)
- **[SRT_SYNTAX]** Subtitle #1: Subtitle starts (6.50s) after video ends (5.64s).
- **[TIMING_DRIFT]** No speech detected inside window (6.50s - 10.50s).
  - *Timestamp:* `0:00:06.500000 --> 0:00:10.500000`
  - *Subtitle:* "Welcome to the automated subtitle quality checking demo."
  - *Spoken Audio:* "[SILENCE / DRIFT]"

### `wrong_text.mp4` (FAIL)
- **[TEXT_MISMATCH]** Segment text discrepancy (137.5% mismatch).
  - *Timestamp:* `0:00:00.500000 --> 0:00:08`
  - *Subtitle:* "Today we are going to learn how to cook Italian pasta with olive oil and garlic."
  - *Spoken Audio:* "wants to climb that slide or the ladder and you're saying be careful What does that mean to the child be careful?"
- **[TEXT_MISMATCH]** Segment text discrepancy (157.1% mismatch).
  - *Timestamp:* `0:00:08.500000 --> 0:00:18`
  - *Subtitle:* "Make sure the water is boiling before adding salt and pasta into the pot."
  - *Spoken Audio:* "child supposed to do except maybe freeze Whereas if you said that ladder is quite tall You need to make sure you know"

### `wrong_timing.mp4` (FAIL)
- **[TEXT_MISMATCH]** Segment text discrepancy (93.3% mismatch).
  - *Timestamp:* `0:00:12 --> 0:00:16.500000`
  - *Subtitle:* "The child wants to climb that slide or the ladder, and you're saying, "Be careful.""
  - *Spoken Audio:* "said that ladder is quite tall You need to"
- **[TEXT_MISMATCH]** Segment text discrepancy (100.0% mismatch).
  - *Timestamp:* `0:00:16.500000 --> 0:00:23.200000`
  - *Subtitle:* "What does that mean to the child, "Be careful"? What is the child supposed to do except maybe freeze?"
  - *Spoken Audio:* "make sure you know you're holding the side railings Now you've given him something very"

