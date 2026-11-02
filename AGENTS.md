# Burmese Voice Kit, instructions for Codex

This repo turns a Burmese (Myanmar) script into a natural voiceover with ElevenLabs Eleven v4. It does not make sound by itself: the voice comes from the user's own ElevenLabs account, through an ElevenLabs MCP server in Codex or `ELEVENLABS_API_KEY`. If neither exists, stop and point the user to "Connect ElevenLabs" in README.md. Never fake audio.

Load the `burmese-voice` skill in `.agents/skills/burmese-voice/` and follow its workflow:

1. `python scripts/prepare.py script.txt`, read `work/report.txt`, show the flags to the user, never auto-fix them, never write Burmese prose for them.
2. Generate one paragraph per call, one take each (MCP text to speech with model Eleven v4, or `python scripts/generate.py`). Never re-call to retry; every call costs credits. Keep raws in `work/raw/`.
3. `python scripts/scan_repeats.py work`.
4. Transcript check on every paragraph (`python scripts/check_transcript.py`, or MCP speech to text saved to `work/transcripts/pNN.txt` and `--reuse`).
5. Re-voice only failed paragraphs, after the user says yes. Try `python scripts/join.py cut` first when the only fault is a doubled ending.
6. `python scripts/join.py join`, then remind the user to check the last 3 seconds.

Report one line per paragraph: id, status (passed, cut, re-voiced, failed), what the user still has to listen to, and the final file path.
