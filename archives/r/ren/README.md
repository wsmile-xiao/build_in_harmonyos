# ren

ren renames many files in one directory at once. The search pattern accepts
the `*` and `?` wildcards, and the replacement pattern refers to the text
matched by the n-th wildcard as `#n`:

```bash
ren '*.txt' '#1.md'          # a.txt -> a.md, b.txt -> b.md
ren 'abc*.*.*' 'xyz#1.#3'    # abc.txt.doc -> xyz.doc
```

All checks run before any rename: colliding replacement names abort the whole
operation, rename chains are ordered, rename cycles are broken with a temporary
name, and renames that would delete an existing file are confirmed
interactively or controlled with `-d` (delete), `-k` (keep) or `-a` (abort).

## Upstream

- Distribution: https://www.ibiblio.org/pub/Linux/utils/file/ren-1.0.tar.gz
- Author: Vladimir Lanin, comp.sources.unix Volume 18, Issue 22 (1988);
  Linux port 1.0 by Rob Schipper (1997)
- License: the archive carries no license text (comp.sources.unix posting)
- Language: C (K&R)

## HarmonyOS adaptation

The recipe builds with the upstream Makefile, passing the OHOS compiler through
`CC` and `-std=gnu89` for the K&R source. musl does not define `MAXNAMLEN` in
`<dirent.h>`, so one patch line includes `<sys/param.h>`. The libc-only tool is
linked as a static PIE.

## Versions

| Version | Status |
|---|---|
| 1.0 | built |
