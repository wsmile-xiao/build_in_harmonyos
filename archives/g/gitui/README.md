# gitui

Blazing fast terminal UI for git written in Rust.

## Installation

Precompiled binary deployment for OpenHarmony/HarmonyOS aarch64.

```bash
# gitui requires libgit2 and related libraries
~/usr/local/bin/gitui --version
```

## Notes

- Dynamically linked musl binary (NEEDED libc.musl-aarch64.so.1)
- Requires: libgit2, libssh2, libllhttp, oniguruma, openssl, libgcc
- Custom qsort_r shim provided for HarmonyOS musl libc compatibility

## Links

- GitHub: https://github.com/extrawurst/gitui
- Alpine package: https://pkgs.alpinelinux.org/package/edge/community/aarch64/gitui
