# SCOTCH 7.0.12 adaptation notes

## Configuration

- Build the threaded static graph-partitioning libraries with zlib, bzip2, and LZMA input support.
- Disable Fortran, MPI/PT-SCOTCH, EsMUMPS, and METIS compatibility; enable the sequential upstream CTest suite.
- Use the portable C library interfaces on HarmonyOS PC.
- Patch the two upstream check programs that call `tmpfile()` so they use POSIX `mkstemp`/`fdopen` in the CTest working directory while preserving the same graph mapping and ordering assertions.

## Verification

- The consumer test calls `SCOTCH_version` and checks all version components.
- The sequential upstream CTest suite remains enabled; the OHOS temporary-file patch keeps the graph mapping and ordering tests executable instead of excluding them.
- Python syntax, recipe structure, source SHA-256, and whitespace are checked locally.
- The official OHOS armv8 pipeline remains authoritative for the full build result.
