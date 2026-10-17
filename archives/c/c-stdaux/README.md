# c-stdaux

c-stdaux provides auxiliary macros and functions for the C standard library
(four public headers, header-only). It is part of the c-util project family.

This archive entry adapts c-stdaux 1.6.0 for OpenHarmony PC through a
Conan/Meson package (header-only, upstream meson test suite executed in
`build()`). It serves as the hard dependency of c-rbtree 3.2.0
(`dependency('libcstdaux-1')`).
