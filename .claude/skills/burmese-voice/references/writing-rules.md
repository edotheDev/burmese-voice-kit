# Writing rules for Eleven v4 Burmese

These come from real runs. They are rules of thumb, not guarantees. Your voice may differ, so test.

## 1. Numbers

Always spell numbers as Burmese words in the text sent to the voice. Never use Myanmar digits or Latin digits, digits cause voice errors. `scripts/numbers_my.py` does the conversion (0 to 9,999,999), and `prepare.py` runs it for you. Larger numbers and decimals are flagged, write those by hand.

A spelled-out year at the very start of a take was misheard more often than the same year in the middle of a script. Avoid opening a paragraph on a year.

## 2. Write the way people talk

Use the spoken register (တယ် / ပါတယ်), not the literary သည်. Write full flowing sentences joined with ၊ and connectors. Choppy one-clause lines sound AI-generated.

## 3. English loanwords

Words people really say in English stay in English (AI, video, message, comment, reply). Spell them correctly and capitalise them (Video, Account). Misspelled English is read wrongly.

## 4. Expression tags

Eleven v4 uses the same `[tag]` syntax as v3.

- A tag describes delivery, not an action. Not `[leaning in]`.
- No hyphens inside a tag.
- Keep tags calm for talk and explainer content: `[calm]` `[casual]` `[warm]` `[thoughtful]` `[sincere]` `[curious]` `[lightly amused]`.
- Avoid `[softly]`. On some cloned voices it comes out as a whisper.
- Do not stack tags like `[pointed]` + `[frustrated]`. It sounds angry.
- No CAPS stress words in Burmese.
- Use an ellipsis `...` for a breath pause.

`prepare.py` flags hyphenated tags and the risky list: softly, whispers, pointed, frustrated, angry.

## 5. Paragraph length

One paragraph per API call, each under about 40 s of audio.

Why: a whole 11-paragraph script sent in one call came back 5:18 instead of about 3:50, with a skipped stretch and paragraphs looped two or three times. In another run the last sentence of a roughly 60 s paragraph came back said twice, plus an extra tail. Short paragraphs fixed both.

Burmese reads slow. `prepare.py` estimates length from characters (about 1,000 characters is 60 s). That is a rough guess, calibrate it with `--sec-per-char` once you have heard your voice. When a paragraph is too long it suggests split points at ။ sentence ends.

## 6. Lexicon and homophones

`lexicon.tsv`: some words must be written the way they sound, not the dictionary spelling, or v4 misreads them. Example: v4 read သန်းရာချီ as a number, so it is written သန်းပေါင်းရာချီ. Always write နဲ instead of နည်း: v4 only pronounces it right in the spoken spelling (this one is a native speaker's rule, and it covers words like နည်းနည်း too). Add your own only after testing in your voice. Invented entries are dangerous.

`homophones.tsv`: tone homophones can flip the meaning. Add the pairs you find; `prepare.py` flags every match for you to decide, it never rewrites them.
