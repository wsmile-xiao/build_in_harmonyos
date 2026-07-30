# alsa-lib 1.2.16.1 upstream test inventory

## Registered execution entries

Automake registers exactly two entries through `TESTS` in
`test/lsb/Makefile.am`. They are the only upstream entries that `make check`
executes automatically.

| ID | Program | Source | Registration | Current result |
|---|---|---|---|---|
| `AL-UP-001` | `config` | `test/lsb/config.c` | `TESTS = config` | PASS (target r35) |
| `AL-UP-002` | `midi_event` | `test/lsb/midi_event.c` | `TESTS += midi_event` | PASS (target r35) |

`config` invokes 30 internal routines and `midi_event` invokes six. Each owns
one executable, one Automake result, and one terminal status, so the routines
and assertions are not split into additional cases.

## Build-only programs

Root `test/Makefile.am` declares the following 19 `check_PROGRAMS` but does not
add them to `TESTS`:

| ID | Program |
|---|---|
| `AL-BUILD-001` | `control` |
| `AL-BUILD-002` | `pcm` |
| `AL-BUILD-003` | `pcm_min` |
| `AL-BUILD-004` | `latency` |
| `AL-BUILD-005` | `seq` |
| `AL-BUILD-006` | `seq-ump-example` |
| `AL-BUILD-007` | `playmidi1` |
| `AL-BUILD-008` | `timer` |
| `AL-BUILD-009` | `rawmidi` |
| `AL-BUILD-010` | `midiloop` |
| `AL-BUILD-011` | `umpinfo` |
| `AL-BUILD-012` | `oldapi` |
| `AL-BUILD-013` | `queue_timer` |
| `AL-BUILD-014` | `namehint` |
| `AL-BUILD-015` | `client_event_filter` |
| `AL-BUILD-016` | `chmap` |
| `AL-BUILD-017` | `audio_time` |
| `AL-BUILD-018` | `user-ctl-element-set` |
| `AL-BUILD-019` | `pcm-multi-thread` |

Compiling these programs is build evidence. None is counted as an executed
test until it has deterministic arguments, prerequisites, timeout, oracle,
cleanup, and an independently retained result.

Target r35 built all 19 programs in shared mode. Static mode built 18 and
excluded only `oldapi`, whose source requests the shared-library symbol version
`snd_pcm_hw_params_get_access@ALSA_0.9`. This build-only difference does not
remove or alter either registered upstream execution entry.

## Source evidence

| File | SHA256 |
|---|---|
| `test/Makefile.am` | `43479fc2ccc6d6c00a2f937faf9101c985dabca27bb998c11b619f1ee203fdcc` |
| `test/lsb/Makefile.am` | `d6deb3541b69a9bfa17992868242a4ed13751830834dd659ca9a24358ecffb6f` |
| `test/lsb/config.c` | `c37ca423a33b40c6c6a7a1ec5b6a6ee26cc35f09b32527a6cebdaef5ce184a64` |
| `test/lsb/midi_event.c` | `a70d2be2b41733e24eb060e4e41f9030f33d7c22f8bb18212766fd7d35bed544` |

Current upstream result: `2/2 PASS` on the OpenHarmony PC target in both shared
and static fresh W3 r35 builds. Together with the 11 independent package
consumers, the target logical result is `13/13 PASS`; shared/static reruns are
not added together.
