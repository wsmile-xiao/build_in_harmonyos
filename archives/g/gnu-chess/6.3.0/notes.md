# GNU Chess 6.3.0

- Builds the command-line engine without optional readline and gettext
  integrations.
- A weak-symbol feature check preserves `pthread_cancel` where the POSIX
  implementation provides it. Otherwise, the non-terminating engine and
  adapter workers and the potentially blocked input reader are detached so
  process shutdown cannot wait forever.
- The release contains no automated upstream test suite.
- The consumer checks version/help output and verifies that help documents the
  `--uci` mode. Interactive UCI protocol execution is deferred until an OHOS
  arm64 runtime target is connected.
- Local OHOS arm64 `conan create` completed successfully and produced an
  AArch64 ELF engine. Upstream test count is 0 because the release provides no
  automated suite; the CLI help/version checks run locally, while interactive
  UCI runtime checks are deferred because no OHOS arm64 HDC target is connected.
- Native OHOS builds place Autoconf temporary directories and files under the
  worker `TMPDIR` and use the repository's E011 `umask 022` workaround so
  `config.status` can create and read its generated awk programs on HMDFS.
- Official OHOS test and CI results remain pending.
