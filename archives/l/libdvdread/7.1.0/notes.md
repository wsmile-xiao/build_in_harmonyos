# libdvdread 7.1.0 adaptation notes

The immutable VideoLAN release builds with its upstream Meson files.
`libdvdcss` is optional upstream and is disabled because no corresponding
published Conan dependency is available; unencrypted directory/image access
remains supported.

The upstream release contains no test directory or test target. The added
consumer links the installed public target, verifies the 7.1.0 API macros,
opens an existing directory through `DVDOpen`, checks failure for a missing
title, and exercises a nonexistent-path fault scenario.
