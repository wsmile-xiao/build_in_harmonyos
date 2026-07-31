# mbrola-gr2 0.0.20010521 adaptation notes

## Source

- Upstream project: https://github.com/numediart/MBROLA-voices
- Maintained source package: Debian TTS team `0.0.20010521+repack2-6`
- Source archive: `mbrola-gr2_0.0.20010521+repack2.orig.tar.xz`
- SHA256: `0236fae65ada3b70900c35d9faf98c40b51372ed41230277eb9aba0f59260820`

The Debian source package retains the upstream GR2 database, README, license,
and PHO example while removing unrelated historical packaging material.

## License

GR2 uses a voice-specific restrictive license, represented as
`LicenseRef-MBROLA-GR2`. It permits speech synthesis only with MBROLA, requires
the license notice to accompany redistribution, and prohibits sale or
incorporation into a sold product without prior permission from the database
owners. The unmodified `license.txt` is installed under `licenses/`.

## Package layout

| Path | Purpose |
|---|---|
| `share/mbrola/gr2/gr2` | MBROLA GR2 diphone database |
| `share/mbrola/gr2/TEST/DEMOST~1.PHO` | Upstream phoneme/prosody example |
| `share/doc/mbrola-gr2/README.txt` | Upstream voice documentation |
| `licenses/license.txt` | Upstream redistribution terms |

The package is architecture-independent data. It produces no library or
executable and has no Conan dependency.

## Upstream tests

This release has no automated upstream test runner. It provides one manual PHO
example containing 211 phoneme commands. The example is retained unchanged and
used by the Conan consumer test for deterministic database-coverage checks.

## Consumer validation

`test_package/test_mbrola_voice.py` parses the packaged MBROLA binary format
instead of checking file presence only. It validates:

- the `MBROLA` magic and format version `2.060`;
- 1081 unique diphone index records and 19597 pitch-mark frames;
- the 22050 Hz sample rate, period, coding, and raw-data boundaries;
- the embedded GR2 metadata;
- all 211 upstream PHO commands, including every adjacent diphone transition;
- the required voice-specific license terms.

## Synthesis status

The upstream PHO example is preserved but is not executed by this Conan
recipe. The MBROLA engine is a separate runtime and is not available as a
Conan dependency in this repository. The upstream synthesis rate is therefore
reported as 0/1 executed, not as a pass. The deterministic consumer still
parses all 211 commands and verifies every adjacent diphone transition against
the packaged GR2 database.
