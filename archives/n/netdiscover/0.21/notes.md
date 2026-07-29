# netdiscover 0.21

- The release contains Automake inputs but no generated `configure` script, so
  a CMake wrapper builds the exact upstream source list.
- The package uses the published `libpcap/1.10.6` dependency and
  POSIX threads.
- Upstream provides no automated tests. The consumer exercises the help/version
  path without requiring root privileges or opening a network interface.
- Local OHOS arm64 `conan create` completed successfully: the nine-step CMake
  build linked an AArch64 executable against the packaged libpcap dependency.
  Upstream test count is 0 because the release provides no automated suite;
  consumer runtime execution is deferred because no OHOS arm64 HDC target is
  connected.
- Official OHOS test and CI results remain pending.
