---
name: burmese-voice
description: Make a natural Burmese (Myanmar) voiceover with ElevenLabs Eleven v4 text to speech (TTS). Use when the user wants a Burmese or Myanmar voiceover, narration, or TTS from a script, mentions ElevenLabs v4 reading Burmese wrongly, numbers or tone homophones misread, or paragraphs that loop, repeat or skip.
---

# Burmese voice with Eleven v4

Turns a Burmese script into a clean voiceover. The kit's scripts live in `scripts/`. Do the steps in order and report per paragraph.

Read `references/writing-rules.md` before editing any script text, and `references/qa.md` before judging a result.

## Workflow

1. Check the script file. Paragraphs are separated by a blank line. If the user wrote it in a hurry, apply the writing rules, but never rewrite their meaning. Do not write Burmese prose for them unless asked.
2. Prepare: `python scripts/prepare.py script.txt`. This applies `lexicon.tsv`, converts numbers to Burmese words, writes `work/pNN.txt` and `work/report.txt`. Read the report. The flags are never auto-fixed: long paragraphs, leftover digits, homophones, ALL CAPS words, bad or risky tags. Fix the script text with the user, then run prepare again. Numbers of 10,000,000 or more and decimals must be written by hand.
3. Generate: `python scripts/generate.py` (one paragraph per API call, one take each). Needs `ELEVENLABS_API_KEY` and a voice id (`--voice-id` or `ELEVENLABS_VOICE_ID`). Never print the key.
4. Scan: `python scripts/scan_repeats.py work`. REPEAT hits are almost always real. Suspect hits need listening.
5. Transcript check: `python scripts/check_transcript.py` for every paragraph. Never skip it, short paragraphs fail too. If there is no key budget, give the user the manual Gemini route from the README.
6. Re-voice only failed paragraphs: `python scripts/generate.py --only p03,p07 --force`. Ask the user before spending credits on a batch. Never regenerate a paragraph that passed. For a doubled ending, try a cut first: `python scripts/join.py cut p03 --cut START END`.
7. Join: `python scripts/join.py join`. Then check the last 3 seconds of the final file.

## Rules that matter most

- One paragraph per call, each under about 40 s of audio.
- Numbers always as Burmese words. Do not open a take on a year.
- Spoken register, flowing sentences. English loanwords stay in English, spelled correctly.
- Calm delivery tags only, no hyphens inside tags.
- Keep raw files in `work/raw/`. Cuts always read from the raw file.
- Add lexicon entries only after testing them in the user's own voice.

Report back as a short list: paragraph id, status (passed, cut, re-voiced, failed), and what is left for the user to listen to.
