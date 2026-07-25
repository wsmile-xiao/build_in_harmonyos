# libsoxr 0.1.3 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出动态 libsoxr.so，供 dlopen 及作依赖。

## 关键适配
- 老 CMakeLists → `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`
- 关 openmp/tests/examples/lsr-bindings
- doc 装到 `CMAKE_INSTALL_FULL_DOCDIR` 绝对路径 → configure 就设 `-DCMAKE_INSTALL_PREFIX=<pkg>`
- 自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain（os=OHOS 下 CMAKE_SYSTEM_NAME 映射 cmake 不认，ML-0035）
- 产出 .so 用 binary-sign-tool 自签（鸿蒙 PC XPM 要求 dlopen 的 .so 代码签名）

## 状态
built（CI conan create + test 通过）
