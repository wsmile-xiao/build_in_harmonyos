# Release Note - yt-dlp 2026.03.17

## Release Information

- Version: 2026.03.17
- Release Date: 2026-03-17
- Source: https://github.com/yt-dlp/yt-dlp
- Platform: OpenHarmony (aarch64)

## Changes

This is the latest stable release of yt-dlp for OpenHarmony.

### Features

- Self-contained Python zipapp (no installation required)
- Supports hundreds of video platforms
- Video/audio extraction in various formats
- Subtitle downloading
- Metadata embedding

### Platform Notes

- No modifications required for OpenHarmony
- Runs directly with Python 3.8+
- No external dependencies beyond Python

## Installation

```bash
# Extract the precompiled package
tar xzf yt-dlp-2026.03.17-ohos-aarch64.tar.gz -C $HOME/usr/local

# Verify
yt-dlp --version
```

## Files Included

- bin/yt-dlp - Main executable
- share/man/man1/yt-dlp.1 - Man page
- share/bash-completion/completions/yt-dlp - Bash completion

## Known Issues

None.