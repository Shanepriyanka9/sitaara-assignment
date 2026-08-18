# Video & Subtitle Batch QC Report

**Summary:** Total: 8 | ✅ PASS: 1 | ⚠️ NEEDS REVIEW: 1 | ❌ FAIL: 6

## Overview

| File | Status | Global WER | Defects Found |
| :--- | :---: | :---: | :---: |
| `empty_subtitle.mp4` | ❌ FAIL | N/A | 1 |
| `good.mp4` | ❌ FAIL | 3.5% | 10 |
| `missing_subtitle.mp4` | ❌ FAIL | N/A | 1 |
| `video1.mp4` | ✅ PASS | 0.0% | 0 |
| `video2.mp4` | ❌ FAIL | 100.0% | 1 |
| `video3.mp4` | ⚠️ REVIEW | 0.0% | 2 |
| `wrong_text.mp4` | ❌ FAIL | 453.3% | 2 |
| `wrong_timing.mp4` | ❌ FAIL | 320.6% | 2 |

## Actionable Defect Breakdown

### `empty_subtitle.mp4` (FAIL)
- **[INVALID_SRT]** Subtitle file is empty.

### `good.mp4` (FAIL)
- **[TEXT_MISMATCH]** High text discrepancy (60.0% mismatch).
  - *Timestamp:* `0:00:00 --> 0:00:04.500000`
  - *Subtitle:* "The child wants to climb that slide or the ladder, and you're saying, "Be careful.""
  - *Spoken Audio:* "The child wants to climb that slide or the ladder, and you're saying, be careful. What does that mean to the child be careful?"
- **[TIMING_DRIFT]** Timing drift of 4.50s (Subtitle at 4.50s, Speech started at 0.00s).
  - *Timestamp:* `0:00:04.500000 --> 0:00:11.200000`
  - *Subtitle:* "What does that mean to the child, "Be careful"? What is the child supposed to do except maybe freeze?"
  - *Spoken Audio:* "The child wants to climb that slide or the ladder, and you're saying, be careful. What does that mean to the child be careful? What is the child supposed to do except maybe freeze? Whereas if you said that ladder is quite tall, you need to make sure, you know,"
- **[TIMING_DRIFT]** Timing drift of 3.20s (Subtitle at 11.20s, Speech started at 8.00s).
  - *Timestamp:* `0:00:11.200000 --> 0:00:21.500000`
  - *Subtitle:* "Whereas if you said, "That ladder is quite tall. You need to make sure, you know, you're holding the side railings.""
  - *Spoken Audio:* "What is the child supposed to do except maybe freeze? Whereas if you said that ladder is quite tall, you need to make sure, you know, you're holding the side feelings. Now you've given him something very specific to do."
- **[TIMING_DRIFT]** Timing drift of 3.50s (Subtitle at 21.50s, Speech started at 18.00s).
  - *Timestamp:* `0:00:21.500000 --> 0:00:25.500000`
  - *Subtitle:* "Now you've given him something very specific to do."
  - *Spoken Audio:* "you're holding the side feelings. Now you've given him something very specific to do. And, you know, they learn through their mistakes."
- **[TIMING_DRIFT]** Timing drift of 4.50s (Subtitle at 25.50s, Speech started at 21.00s).
  - *Timestamp:* `0:00:25.500000 --> 0:00:31.500000`
  - *Subtitle:* "And, you know, they learn through their mistakes. That's the whole thing about risky play and the importance of it."
  - *Spoken Audio:* "Now you've given him something very specific to do. And, you know, they learn through their mistakes. That's the whole thing about risky play in the importance of it. Instead of saying, if you run on the road, you'll fall and hurt yourself."
- **[TIMING_DRIFT]** Timing drift of 3.50s (Subtitle at 31.50s, Speech started at 28.00s).
  - *Timestamp:* `0:00:31.500000 --> 0:00:36.500000`
  - *Subtitle:* "Instead of saying, "If you run on the road, you'll fall and hurt yourself,""
  - *Spoken Audio:* "That's the whole thing about risky play in the importance of it. Instead of saying, if you run on the road, you'll fall and hurt yourself. You say, you may fall if you run fast on the road and you'll hurt yourself."
- **[TIMING_DRIFT]** Timing drift of 5.50s (Subtitle at 36.50s, Speech started at 31.00s).
  - *Timestamp:* `0:00:36.500000 --> 0:00:41`
  - *Subtitle:* "you say, "You may fall if you run fast on the road and you'll hurt yourself.""
  - *Spoken Audio:* "Instead of saying, if you run on the road, you'll fall and hurt yourself. You say, you may fall if you run fast on the road and you'll hurt yourself. If they don't listen, they let themselves say,"
- **[TIMING_DRIFT]** Timing drift of 5.00s (Subtitle at 41.00s, Speech started at 36.00s).
  - *Timestamp:* `0:00:41 --> 0:00:43.600000`
  - *Subtitle:* "If they don't listen, they'll hurt themselves."
  - *Spoken Audio:* "You say, you may fall if you run fast on the road and you'll hurt yourself. If they don't listen, they let themselves say, that's the logical consequence that happened."
- **[TIMING_DRIFT]** Timing drift of 2.60s (Subtitle at 43.60s, Speech started at 41.00s).
  - *Timestamp:* `0:00:43.600000 --> 0:00:46.200000`
  - *Subtitle:* "That's the logical consequence that happened."
  - *Spoken Audio:* "If they don't listen, they let themselves say, that's the logical consequence that happened. That's how children learn."
- **[TIMING_DRIFT]** Timing drift of 3.20s (Subtitle at 46.20s, Speech started at 43.00s).
  - *Timestamp:* `0:00:46.200000 --> 0:00:53.500000`
  - *Subtitle:* "That's how children learn. That's how children can evaluate. That's how children can make choices."
  - *Spoken Audio:* "that's the logical consequence that happened. That's how children learn. That's how children can evaluate. That's how children can make choices."

### `missing_subtitle.mp4` (FAIL)
- **[INVALID_SRT]** Subtitle file is missing.

### `video2.mp4` (FAIL)
- **[TEXT_MISMATCH]** High text discrepancy (100.0% mismatch).
  - *Timestamp:* `0:00:00.500000 --> 0:00:04.500000`
  - *Subtitle:* "This is a completely different recipe for baking chocolate cookies."
  - *Spoken Audio:* "Welcome to the automated subtitle quality checking demo."

### `video3.mp4` (NEEDS_REVIEW)
- **[SRT_SYNTAX]** Subtitle #1: Subtitle starts (6.50s) after video ends (5.64s).
- **[NO_SPEECH_DETECTED]** Subtitle #1 displayed text but no speech was detected in audio.
  - *Timestamp:* `0:00:06.500000 --> 0:00:10.500000`
  - *Subtitle:* "Welcome to the automated subtitle quality checking demo."
  - *Spoken Audio:* "[SILENCE]"

### `wrong_text.mp4` (FAIL)
- **[TEXT_MISMATCH]** High text discrepancy (206.2% mismatch).
  - *Timestamp:* `0:00:00.500000 --> 0:00:08`
  - *Subtitle:* "Today we are going to learn how to cook Italian pasta with olive oil and garlic."
  - *Spoken Audio:* "The child wants to climb that slide or the ladder, and you're saying, be careful. What does that mean to the child be careful? What is the child supposed to do except maybe freeze?"
- **[TIMING_DRIFT]** Timing drift of 3.50s (Subtitle at 8.50s, Speech started at 5.00s).
  - *Timestamp:* `0:00:08.500000 --> 0:00:18`
  - *Subtitle:* "Make sure the water is boiling before adding salt and pasta into the pot."
  - *Spoken Audio:* "What does that mean to the child be careful? What is the child supposed to do except maybe freeze? Whereas if you said that ladder is quite tall, you need to make sure, you know, you're holding the side feelings."

### `wrong_timing.mp4` (FAIL)
- **[TIMING_DRIFT]** Timing drift of 4.00s (Subtitle at 12.00s, Speech started at 8.00s).
  - *Timestamp:* `0:00:12 --> 0:00:16.500000`
  - *Subtitle:* "The child wants to climb that slide or the ladder, and you're saying, "Be careful.""
  - *Spoken Audio:* "What is the child supposed to do except maybe freeze? Whereas if you said that ladder is quite tall, you need to make sure, you know,"
- **[TIMING_DRIFT]** Timing drift of 5.50s (Subtitle at 16.50s, Speech started at 11.00s).
  - *Timestamp:* `0:00:16.500000 --> 0:00:23.200000`
  - *Subtitle:* "What does that mean to the child, "Be careful"? What is the child supposed to do except maybe freeze?"
  - *Spoken Audio:* "Whereas if you said that ladder is quite tall, you need to make sure, you know, you're holding the side feelings. Now you've given him something very specific to do."

