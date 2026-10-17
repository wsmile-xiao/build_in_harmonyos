# rats

RATS (Rough Auditing Tool for Security) is a C/C++ (and other languages) source-code
security audit scanner. It scans source files for potentially dangerous function calls
and reports them with severity ratings, using an XML vulnerability database
(`rats-*.xml`) parsed via expat.

## OHOS adaptation

- Autotools project with pre-generated `configure` + `Makefile.in` (no `Makefile.am`,
  no automake needed); lexers are pre-generated, so flex is not required either.
- The `expat` include path is merged into `CFLAGS` because `Makefile.in` only
  references `$(CFLAGS)`, not `$(CPPFLAGS)`.
- OHOS cross build requires explicit `--host=aarch64-unknown-linux-ohos
  --build=x86_64-pc-linux-gnu` to force cross mode (conan-verify uses the same host
  profile for both, which otherwise makes autoconf try to run probe binaries), plus an
  explicit `--prefix={package_folder}` to override the toolchain-injected `/`.
- `bin/rats` is self-signed for OHOS ELF execution; it depends on `expat/2.8.4`.
- Upstream `--help` exits with code 1 (`usage(); exit(1)`); the end-to-end test checks
  the output content rather than the exit code.

## Dependencies

- `expat/2.8.4` — XML parser used to load the vulnerability database (`rats-*.xml`)

## References

- https://github.com/andrew-d/rough-auditing-tool-for-security
