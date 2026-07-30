# openobex 1.7.2

- Builds the static core library with the portable INET, custom, and
  file-descriptor transports.
- Bluetooth, IrDA, USB, Linux udev integration, applications, and
  documentation are disabled because they require optional host facilities.
- The legacy CMake 3.1 policy floor is raised to 3.5 for current CMake
  compatibility without changing project behavior.
- The release contains demonstration applications but no automated upstream
  test suite. A deterministic in-memory API consumer is provided.
- Local OHOS arm64 `conan create` completed successfully: all 20 library build
  steps and the consumer compile/link passed. Upstream test count is 0 because
  the release provides no automated tests; consumer runtime execution is
  deferred because no OHOS arm64 HDC target is connected.
- Official OHOS test and CI results remain pending.
