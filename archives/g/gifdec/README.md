# gifdec

Minimalist C library for reading GIF files (lecram/gifdec, public domain).

- Upstream: https://github.com/lecram/gifdec (master-only, public domain)
- Form factor: two files — `gifdec.c` (530 lines, decoder implementation) + `gifdec.h` (public API). NOT a header/source hybrid: no implementation macro needed by consumers.
- Public API: `gd_open_gif` / `gd_get_frame` / `gd_render_frame` / `gd_is_bgcolor` / `gd_rewind` / `gd_close_gif` (+ optional `plain_text` / `comment` / `application` extension hooks on the `gd_GIF` struct)
- Zero third-party dependencies (POSIX fd I/O + libc `mem*`, no libm), no build system upstream
- Conan package ships a thin static library built from the unmodified upstream `gifdec.c` plus the public header under `include/`
- Supports all standard GIF features incl. interlace, local color tables, GCE transparency/disposal, NETSCAPE loop extension; known upstream limitation: files without a global color table are rejected

## Consuming

```c
#include "gifdec.h"

gd_GIF *gif = gd_open_gif("anim.gif");
while (gd_get_frame(gif) > 0) {
    uint8_t *rgb = malloc(gif->width * gif->height * 3);
    gd_render_frame(gif, rgb);   /* 3 bytes/pixel canvas */
    free(rgb);
}
gd_close_gif(gif);
```

With the Conan package, link `gifdec::gifdec` (symbols already compiled into the static library — do NOT compile `gifdec.c` yourself).

## Versions

| Version | Upstream snapshot | Status |
|---------|-------------------|--------|
| 0.0-git.1dcbae1 | master @ 1dcbae19363597314f6623010cc80abad4e47f7c | built |
