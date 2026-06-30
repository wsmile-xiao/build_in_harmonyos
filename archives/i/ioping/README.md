# ioping

I/O latency measuring tool.

ioping measures I/O latency of storage devices using simple I/O operations similar to those used in everyday tasks.

- **Version**: 1.3
- **Language**: C
- **Build system**: Makefile (no configure)
- **Dependencies**: None (links -lm -lrt)
- **Source**: https://github.com/koct9i/ioping

## Build Notes

- Pure Makefile project, no configure script
- Default CC=gcc, override with CC=clang for HarmonyOS
- No source modifications required
