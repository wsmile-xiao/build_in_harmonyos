# minimp3

Minimalist single-file MP3 decoder (pull-based, header/source hybrid).

- Upstream: https://github.com/lieff/minimp3 (master branch, CC0 1.0 / public domain)
- Form factor: two headers — `minimp3.h` (core decoder, `MINIMP3_IMPLEMENTATION` activates the implementation section) + `minimp3_ex.h` (buffer/stream/file convenience API)
- Zero third-party dependencies (libc/libm only), no build system upstream
- Conan package ships a thin static library built from one amalgamated TU plus the two public headers under `include/`

## Consuming

```c
#define MINIMP3_IMPLEMENTATION /* only if you compile the TU yourself */
#include "minimp3_ex.h"
```

With the Conan package, link `minimp3::minimp3` (implementation already compiled into the static library — do NOT define `MINIMP3_IMPLEMENTATION` in consumer code).

## Versions

| Version | Upstream snapshot | Status |
|---------|-------------------|--------|
| 0.0-git.ea99364 | master @ ea99364f61c14656440e8d77e9c233ccf3124633 | built |
