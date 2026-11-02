# QA for a Burmese voiceover

## Every paragraph, every time

1. Scan every paragraph for repeats: `python scripts/scan_repeats.py work`.
   - REPEAT (similarity 0.72 or more): almost always a real loop or doubled phrase. Real loops in v4 Burmese takes scored 0.80 to 0.83.
   - suspect (0.64 to 0.72): clean takes scored up to 0.62, so a suspect needs your ears. A phrase the script really says twice also shows up here.
2. Check every paragraph's transcript: `python scripts/check_transcript.py`. Never skip it. In one real run, 3 of 11 short paragraphs still had a dropped word, a wrong first word, or a number misread. The scan cannot catch those.
   - Scribe is only "Good" on Burmese, so a flag is a pointer, not a verdict. A pass is not proof.
   - Do not use Whisper for Burmese. It is useless for it.
   - Manual alternative: upload ONE clip per fresh Gemini chat and ask for a word-for-word transcript. Several clips in one message get mixed up, and long files truncate around 3 minutes.
3. Re-voice only the failed paragraph: `python scripts/generate.py --only p03 --force`. Never regenerate paragraphs that passed. Credits are expensive, so ask before a batch.

## Cutting a doubled ending

If the last words come back twice, cut instead of re-voicing when you can:

`python scripts/join.py cut p03 --cut START END`

Pick the cut at the deepest dip between the last two quiet syllables. Burmese end particles like ပါ are short and 10 to 20 dB quieter than content words, so the loud bursts are NOT the particles. The deep silences listed by `scan_repeats.py` are the candidate cut points. Listen to the result.

## Keep the raws

Raw generations stay in `work/raw/`. `join.py cut` always reads from the raw file and writes the result to `work/pNN.mp3`, so you can redo a cut with different times without stacking damage.

## Before you ship

- Check the last 3 seconds of the final file: no doubled word, no stray tail, no clipped end.
- Listen to the whole thing once on a phone speaker.

A long single take (anything sent as one big call) can loop a whole stretch 30 s or more later. The default scan only looks 12 s back, which is right for short kit paragraphs; on a long take run `scan_repeats.py --max-offset 60`.
