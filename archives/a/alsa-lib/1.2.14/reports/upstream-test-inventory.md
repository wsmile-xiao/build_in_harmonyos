# alsa-lib 1.2.14 upstream test inventory

Source of truth: the official release archive
`https://www.alsa-project.org/files/pub/lib/alsa-lib-1.2.14.tar.bz2`
(sha256 `be9c88a0b3604367dd74167a2b754a35e142f670292ae47a2fdef27a2ee97a32`),
extracted unmodified before any patch is applied.

## Registered execution entries

Automake registers exactly two entries through `TESTS` in
`test/lsb/Makefile.am`:

```
TESTS  = config
TESTS += midi_event
check_PROGRAMS = $(TESTS)
```

They are the only upstream entries that `make check` executes
automatically.

| ID | Program | Source | Registration | Line |
|---|---|---|---|---|
| `AL-UP-001` | `config` | `test/lsb/config.c` | `TESTS = config` | `test/lsb/Makefile.am:1` |
| `AL-UP-002` | `midi_event` | `test/lsb/midi_event.c` | `TESTS += midi_event` | `test/lsb/Makefile.am:2` |

`config` invokes 30 internal routines and `midi_event` invokes six. Each owns
one executable, one Automake result file and one terminal status, so the
internal routines are not split into additional cases.

## Build-only programs

Root `test/Makefile.am` declares the following 19 `check_PROGRAMS` but does not
add them to `TESTS` (`test/Makefile.am:3-6`):

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
cleanup and an independently retained result.

`oldapi.c` deliberately requests the shared-library symbol version
`snd_pcm_hw_params_get_access@ALSA_0.9`; a static archive exports the ordinary
symbol rather than the shared version node, so static mode omits only this
build-only shared-version probe and still builds the remaining 18 programs.
Neither registered upstream test is removed or modified.

## Source evidence

SHA256 of the four files that define the upstream test boundary. They are
byte-identical between the 1.2.14 release used here and the previously adapted
1.2.16.1 release, i.e. the upstream test boundary did not change.

| File | SHA256 (1.2.14) | SHA256 (1.2.16.1) | Equal |
|---|---|---|---|
| `test/Makefile.am` | `43479fc2ccc6d6c00a2f937faf9101c985dabca27bb998c11b619f1ee203fdcc` | same | yes |
| `test/lsb/Makefile.am` | `d6deb3541b69a9bfa17992868242a4ed13751830834dd659ca9a24358ecffb6f` | same | yes |
| `test/lsb/config.c` | `c37ca423a33b40c6c6a7a1ec5b6a6ee26cc35f09b32527a6cebdaef5ce184a64` | same | yes |
| `test/lsb/midi_event.c` | `a70d2be2b41733e24eb060e4e41f9030f33d7c22f8bb18212766fd7d35bed544` | same | yes |

## Real execution entry

`make check` is the real upstream entry and it is executed inside
`build()` of the recipe, so `conan create` cannot succeed without actually
running it:

```
make -j1 check LOG_COMPILER=/system/bin/timeout AM_LOG_FLAGS=180
```

Both registered entries run under an external 180-second timeout. The recipe
then asserts that the `.trs` result set is exactly
`{test/lsb/config.trs, test/lsb/midi_event.trs}` and that each one carries
`:test-result: PASS`, `:global-test-result: PASS`, `:recheck: no`,
`:copy-in-global-log: no`. A missing, extra, failed or re-checked result makes
the build fail.

See `reports/test-report.md` for the measured per-case results.
