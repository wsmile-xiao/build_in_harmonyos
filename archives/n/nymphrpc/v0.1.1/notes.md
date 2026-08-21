# nymphrpc v0.1.1 适配笔记

## 编译环境
- 构建系统: Makefile（非 autotools/cmake）
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: **built**（已通过真机 CI 验证，conan create PASS，Build Summary 1/1 100%）
- 构建方式: **Conan recipe 化**（v0.1.1/conanfile.py + conandata.yml + test_package/），2026-08-20 重组

## 编译步骤（Conan 方式）

1. 下载源码并解包（conandata.yml 提供 URL + SHA-256 = 63bc35e8...，经设备 codeload×3 + 本机独立网络路径 + 双代理交叉验证）
2. 通过 Conan 管理 POCO 1.15.3 依赖
3. 使用 make lib 构建，传入：
   - CXX=clang++（来自 Conan conf tools.build:compiler_executables，dict 整体读取）
   - AR=llvm-ar
   - CXXFLAGS 包含 -I src、POCO include 路径、libc++ include 路径、-std=c++17
   - LIBS 包含 PocoNet/PocoUtil/PocoFoundation/PocoJSON + -pthread
4. make 以 `-j1` 单线程执行（OHOS SELinux 禁 FIFO，make jobserver 不可用）

## 依赖

- POCO 1.15.3（必需）：PocoNet、PocoUtil、PocoFoundation、PocoJSON
  - 设备 conan cache 已有编译产物（revision 1bd01695）

## 关键问题与解决方案（Conan 化后）

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++14 标准不兼容 | HarmonyOS SDK libc++ 需要 C++17 | 通过 Conan profile 的 compiler.cppstd=17 传入 |
| 2 | make jobserver 失败 | SELinux 禁 FIFO（HMDFS） | make lib -j1 单线程 |
| 3 | conf 冒号子键读取抛异常 | OHOS conan 2.29.1 的 compiler_executables 是 dict | dict 整体读取 + .get() |

## 编译产物

- libnymphrpc.a - 静态库
- libnymphrpc.so.0.1 - 共享库（shared 选项开启时）

## 注意事项

1. POCO 依赖通过 Conan 管理，无需手动安装
2. libc++ include 路径通过 conanfile.py 的 _libcxx_include() 自动发现
3. conandata.yml 无 patches 段；官方 patches/0001-Makefile.patch（手工编译时代产物）文件保留但不被引用

## 上游测试复现说明

上游测试未集成进 Conan build()（test_package/MANIFEST.yml 诚实声明 upstream_test_in_build: false）；真机 FULL_PASS 依据独立报告 run_root/nymphrpc-0.1.1/upstream-test-round-2.md，测试二进制已清理。完整复现步骤：

1. 编译上游测试可执行：make test（编译 test/nymph_test_client 与 test/nymph_test_server，仅编译不运行）。
2. 运行 Catch2 基准：cd test && make run（即 bin/test_performance_nymphrpc_catch2 --benchmark-no-analysis --benchmark-samples 20），结果 1 TEST_CASE + 17 BENCHMARK 全量通过，exit code 0。
3. 成对运行 client/server 功能测试：先后台启动 ./test/nymph_test_server（端口 4004），再前台运行 ./test/nymph_test_client，client 输出 Test completed.，server 日志确认 helloFunction / helloCallbackFunction / arrayFunction / structFunction 全部回调成功。

按上述步骤可在设备上重新复现 FULL_PASS；结果留存于 run_root/nymphrpc-0.1.1/upstream-test-round-2.md。

## 历史信息（官方原始手工编译笔记，2026-06-09）

- 官方 v0.1.1/ 原为手工编译结构（仅 manifest.yaml + notes.md + patches/0001-Makefile.patch）。
- 手工流程：修改 Makefile（POCO include 路径、-std=c++17、-include ohos_fix.h、libc++ 路径），创建 ~/usr/local/include/preinclude/ohos_fix.h（修复 nullptr_t / __promote），移除 ~/usr/local/include/ 中 musl 头文件干扰。
- 2026-08-20 起该版本改为 conan 化配方构建，上述手工补丁方式已废弃，但补丁文件与历史笔记信息保留供追溯。
