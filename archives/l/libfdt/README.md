# libfdt

libfdt is the Flattened Device Tree manipulation library from the
Device Tree Compiler (dtc) project: create, read and modify FDT blobs
(`fdt_create` / `fdt_getprop` / `fdt_setprop` / `fdt_check_header` …).

## OHOS adaptation

- Builds only `make libfdt` (static `libfdt.a` + versioned `libfdt.so.1.7.2`);
  the CLI tools (dtc/fdtdump/fdtget/…) live in the sibling
  `device-tree-compiler/1.7.2` tool package from the same source.
- Drops the GCC-only `-Wsuggest-attribute=format` flag that clang rejects
  under the upstream `-Werror` (same patch as the sibling package).
- Runs the upstream libfdt C suite (`make tests`, 71 binaries) in the recipe
  `build()` and reports real pass/fail counts.

## Dependencies

None.

## References

- https://git.kernel.org/pub/scm/utils/dtc/dtc.git
- https://kernel.org/pub/software/utils/dtc/
- https://github.com/dgibson/dtc
