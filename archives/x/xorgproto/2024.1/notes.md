# Notes — xorgproto 2024.1

## Build Notes

### HMDFS Permission Issue

When using autotools build system, `config.status` failed to create temporary files on HMDFS filesystem:
```
./config.status[842]: can't create ./confXXX/subs1.awk: Permission denied
```

**Solution**: Use meson build system instead, which doesn't have this issue.

### Meson Build Process

```bash
export TMPDIR=/storage/Users/currentUser/hometmp
export CC=/data/service/hnp/bin/clang
export AR=/data/service/hnp/bin/llvm-ar
export STRIP=/data/service/hnp/bin/llvm-strip
export PATH=/data/service/hnp/bin:$PATH

/storage/Users/currentUser/.local/bin/meson setup builddir --prefix=/storage/Users/currentUser/usr/local
ninja install
```

### Platform-specific Configuration

- config.guess and config.sub patched for OpenHarmony recognition
- No actual compilation needed (header-only package)

## Key Files Modified

- config.guess: Added OpenHarmony platform detection
- config.sub: Added ohos suffix recognition