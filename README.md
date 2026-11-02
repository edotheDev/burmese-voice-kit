## မြန်မာလို အတိုချုပ်

ဒီ repo က ElevenLabs v4 နဲ့ မြန်မာအသံ generate လုပ်တဲ့အခါ ပိုပြီး natural ဖြစ်အောင် ကူညီပေးတဲ့ agent နဲ့ skill file တွေပါ။ Claude Code ဒါမှမဟုတ် Codex မှာ သုံးလို့ရပါတယ်။

သတိထားရမှာက ဒီ repo က သူ့ဘာသာ အသံထုတ်ပေးတာ မဟုတ်ပါဘူး။ ကိုယ့် ElevenLabs account ကို connection ထဲမှာ အရင် connect လုပ်ပေးရပါမယ် (အောက်က "Connect ElevenLabs" ကို ကြည့်ပါ)၊ credit ကလည်း ကိုယ့် account ကပဲ သုံးမှာပါ။

ဘာတွေ ပါလဲဆိုရင်:

- ရေးတော့အမှန် ဖတ်တော့အသံ စကားလုံးတွေကို အသံထွက်အတိုင်း ပြောင်းရေးပေးတဲ့ lexicon
- နံပါတ်တွေကို မြန်မာစာလုံးနဲ့ ပြောင်းရေးပေးတာ
- Paragraph ရှည်တွေကို ခွဲပြီး တစ်ခုချင်း generate လုပ်ပေးတာ
- စာကြောင်း နှစ်ခါပြန်ပြောတာ၊ ကျော်သွားတာတွေကို ပြန်စစ်ပေးတာ

---

# Burmese Voice Kit

A free kit that makes ElevenLabs Eleven v4 read Burmese (Myanmar) scripts the way people actually speak.

## What this is, and what it is not

This repo does **not** make a voice by itself. It is a set of agent and skill files for **Claude** (Claude Code) or **Codex**, plus helper scripts. They tell the AI how to write the Burmese script, how to send it to ElevenLabs, and how to check the result.

The voice itself always comes from **your own ElevenLabs account**, and the credits are yours. So before anything else, connect ElevenLabs (next section). Without that connection nothing gets generated.

## What it fixes

Eleven v4 has known trouble with Burmese. This kit handles four things:

- Words whose spoken sound differs from the spelling. A small lexicon (`lexicon.tsv`) maps the written form to the form you want spoken.
- Numbers. Digits get misread, so every number is converted to Burmese words first (`scripts/numbers_my.py`, 0 to 9,999,999).
- Tone homophones that flip the meaning. `homophones.tsv` lists the pairs, and the prepare step flags them for you to check.
- Long paragraphs. A long paragraph can come back with phrases said twice, looped or skipped. The kit generates one short paragraph per call, then scans each result for repeats and checks it against a transcript.

## Connect ElevenLabs

Pick one:

- **Claude (claude.ai, desktop, Claude Code):** Settings > Connectors > add ElevenLabs and sign in. Or, in Claude Code with an API key: `claude mcp add elevenlabs -e ELEVENLABS_API_KEY=your_key -- uvx elevenlabs-mcp`
- **Codex:** add the official ElevenLabs MCP server to `~/.codex/config.toml`:
  ```toml
  [mcp_servers.elevenlabs]
  command = "uvx"
  args = ["elevenlabs-mcp"]
  env = { ELEVENLABS_API_KEY = "your_key" }
  ```
- **Plain API key** (works with both, and without any AI): set `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`, and the scripts call the API directly.

Whichever you use, make sure it can pick the **Eleven v4** model. If your connection only offers older models, use the API key route, because older models do not speak Burmese.

## Requirements

- Python 3.10 or newer
- ffmpeg (and ffprobe) on PATH
- Your own ElevenLabs account, connected as above, and a voice (your own clone or a library voice)

## Quick start with Claude Code or Codex

1. Connect ElevenLabs (above).
2. Clone this repo and open the folder in Claude Code or Codex.
3. Put your Burmese script in `script.txt`, paragraphs separated by a blank line.
4. Say: "make a Burmese voiceover from script.txt"

Claude Code loads the `burmese-voice` skill (`.claude/skills/`) and the `burmese-voice-director` agent (`.claude/agents/`). Codex loads the same skill from `.agents/skills/` and follows `AGENTS.md`. Either one asks before spending credits on re-voicing.

## Quick start without Claude Code

```
pip install -r requirements.txt
export ELEVENLABS_API_KEY=your_key        # Windows PowerShell: $env:ELEVENLABS_API_KEY="your_key"
export ELEVENLABS_VOICE_ID=your_voice_id

python scripts/prepare.py script.txt          # lexicon, numbers, flags -> work/
python scripts/generate.py                    # one request per paragraph -> work/pNN.mp3
python scripts/scan_repeats.py work           # find looped or doubled stretches
python scripts/check_transcript.py            # optional: Scribe transcript vs your text
python scripts/generate.py --only p03 --force # re-voice only a failed paragraph
python scripts/join.py join                   # trim, join with 0.45 s gaps -> work/final.mp3 + .wav
```

Try it first on `examples/script.txt`.

## The scripts

- `numbers_my.py`: integers to Burmese words, Latin and Myanmar digits, `%`. Numbers of 10,000,000 or more and decimals are flagged, not converted.
- `prepare.py`: applies the lexicon, converts numbers, and flags (never auto-fixes) paragraphs over about 40 s, leftover digits, homophones, ALL CAPS words, tags with hyphens and risky tags. Duration is a rough guess from character count (about 1,000 characters is 60 s) and you can calibrate it with `--sec-per-char`.
- `generate.py`: Eleven v4 text to speech, one request per paragraph, up to 4 at a time, retry on 429. One take per paragraph by default.
- `scan_repeats.py`: finds repeated stretches with MFCC self-similarity, and lists deep silences you can cut at. "Suspect" hits need your ears; a phrase the script really says twice also shows up.
- `check_transcript.py`: Scribe transcript compared to your text, with missing and extra spans. Do not use Whisper for Burmese, it is useless for it. If you have no API budget for this, upload ONE clip per fresh Gemini chat and ask for a word-for-word transcript. Several clips in one message get mixed up, and long files truncate around 3 minutes.
- `join.py`: trims silence, joins paragraphs, and has a `cut` subcommand that removes a time range from the untouched raw file with 10 ms crossfades.

## Writing rules and QA

See `.claude/skills/burmese-voice/references/writing-rules.md` and `.claude/skills/burmese-voice/references/qa.md`. Read them even if you do not use Claude Code.

## Add your own words

Add rows to `lexicon.tsv` only after you have tested them in your own voice. Guessed entries can break a word that was fine. The file ships with one verified entry.

## Tests

```
python tests/test_numbers.py
```

## License

MIT
