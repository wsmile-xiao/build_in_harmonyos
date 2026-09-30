# words-en 2.1 adaptation notes

`words-en` is the American English word-list subpackage from Alpine `words`
2.1-r1. Its source is the official GNU Aspell English dictionary release
`2017.08.24-0`; the English source archive also contains the British, Canadian,
and Australian variants used by sibling packages.

The package decodes `en-common.cwl`, `en_US-w_accents-only.cwl`, and
`en_US-wo_accents-only.cwl` directly. It removes Aspell slash-delimited flags,
converts the source's ISO-8859-1 words to UTF-8, deduplicates entries, and
reproduces Alpine's `LC_ALL=C sort -df` order. This avoids a build-time
`aspell-utils` dependency. The resulting list has 123115 entries.

The official Alpine `words-en` 2.1-r1 package was used as a content reference:
the generated word list is byte-for-byte identical (SHA-256
`7316ff93a3dc147ce54d1bde684aa4d321f86f40d008702b9c948a4ff21e7889`).
The upstream data release has no test target. The added consumer tests check
the packaged file, exact content, American spellings, the missing-file path,
and HarmonyOS 6.0/aarch64 runtime identity.
