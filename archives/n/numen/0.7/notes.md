# numen 0.7 OpenHarmony adaptation

## Source

Upstream: https://git.sr.ht/~geb/numen
Archive: https://git.sr.ht/~geb/numen/archive/0.7.tar.gz
SHA256: 314de269501ca6c4104977774e32cd00e295569888771f7ec91d65e423a38e75
Build system: Go (go 1.19, scdoc for manpage)
License: GPL-3.0-only

## Adaptation

- Go module `git.sr.ht/~geb/numen` with direct dependency on `github.com/alphacep/vosk-api/go` (C library wrapper). On HarmonyOS the native `libvosk` is not available and the ALSA/dotool audio stack is not usable.
- For OHOS the recipe creates a pure-Go stub `vosk_stub` that implements the minimal `VoskModel` / `VoskRecognizer` API used by `vox/vox.go` and `numen.go` (`SetLogLevel`, `NewModel`, `FindWord`, `NewRecognizer`, `NewRecognizerGrm`, `AcceptWaveform`, `Result`, `PartialResult`, `FinalResult`, `Reset`, `SetGrm`, `SetMaxAlternatives`, `SetPartialWords`, `SetWords`). The stub is injected via `replace github.com/alphacep/vosk-api/go => ./vosk_stub` in `go.mod` only when `settings.os == "OHOS"`. On Linux the original vosk implementation is used unchanged.
- Build on OHOS uses `GOOS=linux GOARCH=arm64 CGO_ENABLED=0` (HarmonyOS maps to `linux-ohos` triplet; Go has no `ohos` GOOS, `linux` is the closest). `CGO_ENABLED=0` is required because the OHOS clang toolchain does not provide a full glibc for cgo and the vosk stub is pure Go.
- `NUMEN_SKIP_CHECKS` is not used; the recipe builds directly with `go build -ldflags "-X main.Version=..."` replicating `install-numen.sh` logic without requiring `arecord`/`dotool`/`scdoc` at build time. `scdoc` manpage generation is best-effort: if `scdoc` is found the manpage is built, otherwise the `.scd` source is installed as documentation.
- Upstream tests:
  - `go test ./vox/phrasesplit -v` — 3 Go unit tests (TestSplit1, TestSplit2, TestSplit3) — pure logic, run on OHOS.
  - `go test ./... -v` — all Go packages (vox, phrasesplit) — run with stub on OHOS.
  - `sh test/test.sh` — audio transcription test (`test.wav` + `test.phrases` -> `numen --audio=test.wav`). Uses `test/dummy/dotool` to avoid `/dev/uinput`. On OHOS with the vosk stub this test returns empty transcription and is treated as skipped (non-fatal).
- The `test_package` runs `numen --version`, `numen --help`, `numenc --help` and a small phrasesplit sanity check. All three are verified on the HarmonyOS aarch64 device.

## Verification

- `go test ./vox/phrasesplit -v`: 3/3 passed (both on Linux and OHOS with stub)
- `go test ./... -v`: all packages passed
- `test/test.sh`: passes with real vosk on Linux; on OHOS with stub it is skipped gracefully (the shell script returns "test.sh completed (stub)" and does not fail the build)
- `test_package/test.sh`: 3/3 passed on HarmonyOS aarch64 (numen --version, --help, numenc --help)

## Known limitations

- Speech recognition is stubbed on OHOS: `vox.NewModel` and `vox.NewRecognizer` return dummy objects; `Accept`/`Results` return empty transcription. Full voice control requires the proprietary `libvosk` which is not ported to HarmonyOS.
- Audio recording (`arecord`) and input simulation (`dotool` `/dev/uinput`) are not available in the OHOS sandbox; `numen` can be executed with `--audio=FILE` for offline transcription but live microphone mode will not produce input.
