# bmk

bmk is a portable make-family build tool that integrates subdirectory builds without recursive make invocations.

## Version

- `0.1`: adapted for OHOS aarch64.

## OHOS notes

The package provides the `mk` executable and its manual page. It has no third-party library dependencies. The recipe uses the upstream hand-written configure script and validates both bootstrap compilation and a self-hosted rebuild.

## Verification

```bash
mk -h
mk -f Mkfile
```

## References

- https://github.com/realchonk/bmk
- https://github.com/realchonk/bmk/releases/tag/0.1
