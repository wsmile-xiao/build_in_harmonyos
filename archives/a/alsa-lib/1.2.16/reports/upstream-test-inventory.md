# alsa-lib 1.2.16 upstream test inventory

## Registered execution entries

Automake registers exactly two entries through `TESTS` in
`test/lsb/Makefile.am`. They are the only upstream entries that `make check`
executes automatically.

| ID | Program | Source | Registration | Current result |
|---|---|---|---|---|
| `AL-UP-001` | `config` | `test/lsb/config.c` | `TESTS = config` | PASS (target 2026-08-10) |
| `AL-UP-002` | `midi_event` | `test/lsb/midi_event.c` | `TESTS += midi_event` | PASS (target 2026-08-10) |

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
| `AL-BUILD-018` | `midifile` |
| `AL-BUILD-019` | `user-ctl-element-set` |

Shared mode links all 19. Static mode links 18 and intentionally omits
`oldapi` (AL-BUILD-012), whose source requests the shared-library symbol
version `snd_pcm_hw_params_get_access@ALSA_0.9` that a static archive cannot
provide. Neither registered upstream test is removed or modified.
