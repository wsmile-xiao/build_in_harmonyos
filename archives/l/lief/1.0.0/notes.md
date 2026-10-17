# lief 1.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-16
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: built

## 编译步骤

```bash
# 原始构建探索（work 目录）
cmake -S . -B build-ohos -DCMAKE_BUILD_TYPE=Release -DLIEF_TESTS=ON \
  -DLIEF_EXAMPLES=OFF -DLIEF_PYTHON_API=OFF -DLIEF_C_API=ON \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build-ohos -j$(nproc)     # libLIEF.a + unittests 构建成功
cmake --install build-ohos              # 安装到测试前缀

# Conan 配方验证（端到端）
conan create archives/l/lief/1.0.0 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
# → libLIEF 静态库构建成功，test_package 1/1 通过
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build --url=github.com/LIEF 直连超时 | 网络限制 github.com 直连 | 用 gh-proxy.com 镜像下载官方 tarball（sha256 核验一致后放入 TMPDIR/builds），conandata.yml 仍用官方 HTTPS URL |
| 2 | init-build 误判构建系统 autotools | 模板按 URL 猜测 | 手工重写 conanfile.py 为 CMake 配方 |
| 3 | conan-init 模板生成的 conandata.yml sha256="REPLACE..." | 模板未填 | 填实测 sha256 2cf41269...b682abd |
| 4 | lang-preflight 误判 rust | lang_detect 用全树 basename 命中 tools/Cargo.toml | 核实：核心 src/ 364 个 C++ 文件 0 个 Rust，顶层 CMakeLists.txt project(LIEF LANGUAGES C CXX) → 判 cpp，继续 C++ 适配 |
| 5 | test_package test.c 用 C++ API 编译失败 | 模板项目声明 C | 改为 test_lief.cpp + project(test_lief CXX) |
| 6 | test_package 枚举名错误 | LIEF 1.0 API 更名 | 按头文件修正：LIEF::ELF::Header::CLASS::ELF64 |
| 7 | LIEF::ELF::to_json() SIGABRT | OHOS 静态构建下 JSON 序列化对任意输入崩溃（最小 ELF 与官方样例均复现） | 鸿蒙专项测试不依赖 JSON；记录为知识候选 |
| 8 | conan create 后台进程被工具超时中断 | bash 300s 超时杀进程组 | 同步分段续跑 + 断点复用构建目录 |

## 源码修改
无补丁（源码直接按官方 tag 构建成功，无平台修改）。

## 依赖版本
- 三方依赖全部内置于官方 tarball（mbedtls 4.0.0.r0、spdlog 1.17.0、json 3.12.0、frozen、Catch2 3.12.0 等），FetchContent 本地消费
- 无外部 Conan requires

## 验证结果

```bash
# 上游 C++ unittests（13/13 通过，494 断言）
LIEF_SAMPLES_DIR=.../lief-samples ./build-ohos/tests/unittests/unittests
# → All tests passed (494 assertions in 13 test cases)

# 鸿蒙专项测试（解析真实 OHOS SDK ELF）
./ohos_specific_test small-ohos-elf
# → PASS: OHOS ELF parsed OK | class=ELF64 machine=AARCH64 type=3 sections=29 syms=105

# test_package（conan create 内嵌）
# → 1/1 Test #1: test_lief ... Passed
```

## r02 返工：未实例化上游测试最小纳入实证

分析端 r01 验收判定「上游测试用例必须全部通过」不达标（13/772），要求对全部未实例化入口
执行最小纳入并实际运行。r02 实证如下（完整台账见 reports/test-ledger.md）：

### test_runtime_linux（Catch2 1 项）——已最小纳入并实际运行 → SIGSEGV（上游平台条件）

```bash
# 配置（LIEF_RUNTIME=ON，上游要求显式声明平台/架构，缺任一即配置失败）
cmake -S . -B build-runtime -DCMAKE_BUILD_TYPE=Release -DLIEF_TESTS=ON \
  -DLIEF_EXAMPLES=OFF -DLIEF_PYTHON_API=OFF -DLIEF_C_API=ON \
  -DLIEF_RUNTIME=ON -DLIEF_RUNTIME_PLATFORM=linux -DLIEF_RUNTIME_ARCH=arm64
# CONFIGURE_EXIT=0（首两次失败：缺 LIEF_RUNTIME_PLATFORM / LIEF_RUNTIME_ARCH）

# 构建 → BUILD_EXIT=0（unittests 注册 14 用例，从 13 增至 14）

# 运行 → SIGSEGV（RUN_EXIT=139）
./build-runtime/tests/unittests/unittests "lief.test.runtime.linux"
# → test_runtime_linux.cpp:37 SIGSEGV; assertions: 2 | 1 passed | 1 failed
# 根因：Module::from_handle() 将 dlopen 句柄强转 glibc link_map（src/runtime/linux/Module.cpp:310），
#       OHOS musl 加载器句柄布局不同 → 段错误。上游测试对 glibc 内部结构的硬依赖。
# 日志：/storage/Users/currentUser/zhuo/tmp/evidence-runtime-test.log（sha256 6f211005...）
```

### pytest 758 项（LIEF_PYTHON_API=ON）——已实际构建绑定并运行

```bash
# 配置 LIEF_PYTHON_API=ON → CONFIGURE_EXIT=0（Found Python 3.12.9）
# 构建 → BUILD_EXIT=0（产出 _lief.cpython-312-aarch64-linux-ohos.so）
# 绑定装载：直接导入报 "_Py_Dealloc: symbol not found"（本机 python 静态嵌入），
#           LD_PRELOAD=/storage/Users/currentUser/usr/local/lib/libpython3.12.so 后
#           `import lief` 成功（lief 1.0.0-）
# 运行 pytest（LIEF_SAMPLES_DIR + LD_PRELOAD）→ 372 passed, 156 skipped, 191 errors
# 191 errors 全部为 pytest tmp_path fixture 在 HMDFS/tmpfs 无真实 POSIX 临时目录语义
# （候选目录逐项记录：HMDFS chmod 不生效 owner 不匹配、tmpfs mkdir 0700 可建但文件创建
#  被拒 .lock Permission denied、/tmp 100% 满 → 平台阻塞，计分母不计通过）
# 日志：evidence-pytest-run.log（759a6ee9...）、evidence-pytest-tmpdir.log（ba095e06...）
```

## 交付物
- archives/l/lief/1.0.0/conanfile.py（CMake 配方，静态库）
- archives/l/lief/1.0.0/conandata.yml（官方 URL + sha256）
- archives/l/lief/1.0.0/test_package/（test_lief.cpp + MANIFEST.yml）
- archives/l/lief/1.0.0/reports/test-ledger.md（双口径台账）
- archives/l/lief/1.0.0/reports/ohos-test-consumer.md（专项测试+消费者证据）

## 注意事项
- 纯库类型（libLIEF.a），产物只有库文件，无可执行文件 → 不需要 commands.json（R38）
- LIEF::ELF::to_json() 在 OHOS 静态构建崩溃（SIGABRT），JSON API 暂不可用（知识候选）
- basename 为 LIEF（大写），cpp_info.libs = ["LIEF"]
---

**编译结束**: 2026-09-17 13:04
**最终状态**: built
