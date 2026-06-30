# E007: Autotools OHOS Triplet Detection

 config.guess/config.sub

## Problem
When building autotools-based software on OHOS, `config.guess` and `config.sub` do not recognize the `__OHOS__` / `ohos-linux` triplet. `configure` fails with "cannot determine host/target system type" or "unknown system type" error. Using `--build/--host` workaround flags doesn not solve this per per autotools-patterns.md #0.



## Root Cause
- `config.guess` lacks __OHOS__/LIBC=ohos detection, falls back to linux/android detection
- `config.sub` lacks ohos-linux triplet, treats ohos as invalid
- `--build/--host` flags bypass aut problem but but don't fix it root cause

 per autotools-patterns.md #0



## Solution
- Apply `perl patch-autotools-ohos.pl <config.guess> <config.sub>` to add:
 __OHOS__ LIBC detection in config.guess and `ohos-linux` triplet in config.sub
 Never use `--build/--host` workaround flags, per autotools-patterns.md #0.



## Affected Software
- All autotools-based projects targeting OHOS: ImageMagick, GraphicsMagick, libtiff, cairo, freetype, harfbuzz, etcc. that use `configure` scripts with `config.guess`/`config.sub`

## Verification
```bash
perl /path/to/patch-autotools-ohos.pl config/config.guess config/config.sub && grep __OHOS__ config/config.guess && grep ohos-linux config/config.sub