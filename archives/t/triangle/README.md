# Triangle

Triangle is Jonathan Richard Shewchuk's two-dimensional quality mesh generator
and Delaunay triangulator.  It computes exact Delaunay triangulations,
constrained and conforming Delaunay triangulations, Voronoi diagrams and
high-quality triangular meshes using adaptive-precision floating-point
predicates.

- Upstream: https://www.cs.cmu.edu/~quake/triangle.html
- Distribution: https://www.netlib.org/voronoi/triangle.zip (the download the
  author's own page links to)
- Release: 1.6
- License: non-commercial — private, research and institutional use is free;
  redistribution is permitted with the copyright notices preserved; use inside
  a commercial system requires a direct arrangement with the author.  Only the
  recipe lives in this repository; the source is fetched from the official URL.
- Build system: the upstream hand-written `makefile`
- Package form: `bin/triangle` (CLI) plus `lib/libtriangle.a` +
  `include/triangle.h` (embeddable API)

## HarmonyOS PC adaptation

A single portability patch against the upstream `makefile`; `triangle.c`
itself is untouched.

| Change | Why |
|---|---|
| drop `-DLINUX` | it makes `triangle.c` include `<fpu_control.h>` and call `_FPU_SETCW()`, which are glibc/x86-only.  aarch64 has native IEEE double arithmetic, so the x87 precision-control-word adjustment it enables is unnecessary. |
| drop `-I/usr/X11R6/include -L/usr/X11R6/lib` | only the optional X11 "Show Me" viewer needed them; it is not built. |
| `CC ?= cc`, `CSWITCHES = $(CPPFLAGS) $(CFLAGS) $(CSTD)` | let the Conan toolchain supply the compiler and flags. |
| `CSTD = -std=gnu17` | `triangle.c` is K&R C with 124 old-style function definitions, which C23 removed. |

## Usage

Command line:

```sh
triangle -pq input.poly
```

Embeddable API (the caller defines `REAL` before including the header, exactly
as upstream's `tricall.c` does):

```c
#define REAL double
#define VOID void
#define ANSI_DECLARATORS
#include "triangle.h"

struct triangulateio in = {0}, out = {0};
in.numberofpoints = 4;
in.pointlist = points;          /* 2 * numberofpoints REALs */
char switches[] = "zQ";
triangulate(switches, &in, &out, (struct triangulateio *)NULL);
/* ... use out.pointlist / out.trianglelist ... */
trifree(out.pointlist);
trifree(out.trianglelist);
```

See `1.6/notes.md` for the full adaptation record and
`1.6/test_package/MANIFEST.yml` for the upstream test audit.
