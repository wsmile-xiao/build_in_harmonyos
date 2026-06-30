# gifski

gifski is a pngquant-based GIF encoder for nice-looking animGIFs.

## Description

gifski converts video frames to GIF animations using pngquant's quality-preserving quantization algorithms. It produces the highest-quality GIFs with minimal file size, leveraging temporal and spatial dithering to maintain visual quality.

## Homepage

https://gif.ski

## License

AGPL-3.0-or-later

## Versions

| Version | Status | Build Date |
|---------|--------|------------|
| 1.34.0  | built  | 2026-05-25 |

## Build Notes

- Uses Cargo (Rust) build system on HarmonyOS
- Built with `--no-default-features --features binary,gifsicle`
- Requires .cargo/config.toml for OHOS cross-compilation target (clang + lld linker)
- Removed [patch.crates-io] section from Cargo.toml (unreachable ffmpeg-sys-next git repo)
- Updated Cargo.lock dependencies to match available crates.io versions
- ffmpeg video input feature not enabled (requires separate ffmpeg compilation)

## Dependencies

| Dependency | Version | Notes |
|------------|---------|-------|
| imagequant | 4.3.4 | pngquant quantization library |
| gif | 0.13.1 | GIF decoder/encoder |
| clap | 4.5.32 | CLI argument parser |
| resize | 0.8.8 | Image resizing with rayon |

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gifski 1.34.0
```