# memtool 2018.03.0

- The release archive contains Automake inputs but no generated `configure`
  script, so a small CMake build wrapper compiles the three upstream sources.
- Linux-only MDIO access is intentionally disabled; portable memory-mapped file
  access remains enabled.
- A portability patch falls back to POSIX `ftruncate` when a sandboxed
  filesystem permits sparse file extension but rejects `posix_fallocate`.
- Upstream provides no automated tests. The consumer performs version/help
  checks and writes then reads a temporary file through the packaged binary.
- Local OHOS arm64 `conan create` completed successfully and produced the
  packaged AArch64 executable. Upstream test count is 0 because the release
  provides no automated suite; consumer runtime execution is deferred because
  no OHOS arm64 HDC target is connected.
- The fallback addresses the platform CI filesystem restriction without
  weakening the regular-file write/read round-trip assertion.
