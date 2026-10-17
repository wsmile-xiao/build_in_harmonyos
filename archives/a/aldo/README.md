# aldo

Morse code training program — console-based tutor with four exercises: Classic blocks, Koch method, file playback and callsign generation.

- Upstream: https://www.nongnu.org/aldo/
- Version: 0.7.8
- Git: https://git.savannah.gnu.org/git/aldo.git
- Current package: `archives/a/aldo/0.7.8`
- Supported OpenHarmony architecture: armv8

## OHOS adaptation

- Source is the Debian orig tar (git snapshot `v0.7.8`, SHA256 `2c1dca89e4b3fe6b71c9f75d65576ff314b1528fdf94aca84dc5ff7ade77552a`); autoreconf bootstrap generates `configure`
- Patch `config.sub` via AutotoolsToolchain triplet `aarch64-linux-ohos` for HarmonyOS
- Depends on `libao/1.2.2` (OSS backend) for audio output
- Interactive binary `aldo`; test_package validates binary presence via timeout launch

## Dependencies

- `libao/1.2.2`

## References

- https://www.nongnu.org/aldo/
- https://git.savannah.gnu.org/cgit/aldo.git
- https://tracker.debian.org/pkg/aldo
