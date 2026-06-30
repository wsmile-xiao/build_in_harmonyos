# git-lfs

Git extension for versioning large files.

## Description

Git Large File Storage (LFS) replaces large files such as audio samples, videos, datasets, and graphics with text pointers inside Git, while storing the file contents on a remote server like GitHub.com or GitHub Enterprise.

## Features

- Large file versioning: Track large files without bloating the repository
- Faster cloning: Clone repositories faster with only the files you need
- Better Git performance: Smaller repository size for better Git operations
- Seamless integration: Works with your existing Git workflow

## Installation

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- git-lfs 3.7.0
```

## Usage

After installation, initialize git-lfs in your repository:

```bash
git lfs install
git lfs track "*.psd"
git add .gitattributes
git commit -m "Track large files with git-lfs"
```

## Version

- **Current version**: 3.7.0
- **License**: MIT
- **Website**: https://git-lfs.github.com/

## Requirements

- Git >= 2.0.0
- OpenHarmony aarch64 platform

## Technical Notes

- Go statically compiled binary (no RPATH needed)
- ELF signed for OpenHarmony execution
- Manual generation of mancontent_gen.go and tr_gen.go to skip go generate
- CGO_ENABLED=0 for pure static compilation

## Build Dependencies

- Go >= 1.21
- GOPROXY configured for China mirror (https://goproxy.cn)