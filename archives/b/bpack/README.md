# bpack

> Binary data structures (un-)packing library (pure Python)

## Intro

bpack describes binary record layouts declaratively (down to bit level)
and generates encoders/decoders. Backends: stdlib `struct` (default),
optional `bitstruct` / `numpy` / `bitarray`.

## OHOS Adaptation

- Pure Python project, no compilation; install by copying `bpack/` into
  `lib/python3.12/site-packages`.
- Zero mandatory runtime dependencies (stdlib `struct` backend only);
  optional extras (`bs`/`ba`/`np`) not enabled to keep the dependency
  chain closed (R36).
- Upstream pytest suite (`bpack/tests`, 11 files) runs in `build()`
  with `python3 -m pytest bpack/tests -q`.
- No ELF binaries, no strip/sign/RPATH handling.

## Dependencies

| Dependency | Version | Note |
|------------|---------|------|
| python3 | 3.12 | runtime only |

## Functional Verification

```bash
python3 test_bpack.py
```

## References

- [Upstream repo](https://github.com/avalentino/bpack)
- [Docs](https://bpack.readthedocs.io)
- [PyPI](https://pypi.org/project/bpack/1.3.0/)
