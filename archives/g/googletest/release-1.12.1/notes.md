# googletest release-1.12.1 编译笔记（HarmonyOS PC · 标准 Conan cmake）

## 定位
- 产出 C++ 单元测试框架静态库：libgtest.a / libgtest_main.a / libgmock.a / libgmock_main.a，
  供 OHOS 上 C++ 工程的测试编译链接使用。

## 关键适配
- 沿用 lerc/glfw 模式：自发现 ohos.toolchain.cmake + 裸 cmake，绕开 conan_toolchain（ML-0035）。
- `-DCMAKE_INSTALL_LIBDIR=lib`：ohos.toolchain 64 位默认 lib64/，强制 lib/。
- `INSTALL_GTEST=ON` + `BUILD_GMOCK=ON`：安装 gtest/gmock 四库 + GTestConfig.cmake + pkg-config。
- 静态库（BUILD_SHARED_LIBS=OFF）：无 .so，无需 binary-sign-tool 签名。
- **上游框架自测实跑（rule4 整改）**：OHOS 上 `-Dgtest_build_tests=ON -Dgmock_build_tests=ON`，
  在 build() 内对可实跑的「纯逻辑」自测二进制（29 个）逐一 `cmake --build <target>` →
  binary-sign-tool 自签 → 真机实跑；**严格门禁**：任一未构建/未 rc=0 即 raise ConanException
  （CI 显红取证，历次显红见 build #37394/#37407 → 收敛于 #37414 全绿 29/29）。
- 实跑结果（CI build #37414，真机 OHOS aarch64/musl）：29/29 二进制 rc=0，
  `[ PASSED ]` 1706 框架用例；`gtest_skip_test` 3 用例按 GTEST_SKIP 设计全部 SKIPPED（rc=0）；
  `gtest_no_test_unittest` 0 用例验证「无测试程序」路径。
- 过滤串 GTEST_SELFTEST_FILTER：`-*DeathTest*` 等全部为 **1-e 类技术豁免**——
  OHOS musl fork 受限（#7742 brpc 先例）致 death-test 无法运行；OHOS 应用沙箱**无可写 /tmp**，
  gtest-port.cc 硬编码 `mkstemp("/tmp/gtest_captured_stream.XXXXXX")`，捕获 stdout/stderr 用例
  （CaptureTest/ParseFlagsTest/FlagfileTest）SIGABRT，故排除。未纳入实跑清单的其余上游二进制
  （death/fork 类、python 驱动类、非默认编译变体、负向/压力类）原因逐条见 PR_BODY。
- 版本串为上游 tag `release-1.12.1`（任务版本），Conan Version 可正常解析。
- 静态链接顺序须遵守依赖序：gmock_main → gmock → gtest_main → gtest，另需 -lpthread。

## 状态
verified — GitCode CI 真机 build #37414 conan-build-test 通过（29/29 上游自测子集严格门禁 + test_package 4 断言）
