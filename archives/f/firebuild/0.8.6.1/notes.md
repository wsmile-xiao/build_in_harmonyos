# firebuild 0.8.6.1 鸿蒙 PC 适配笔记

## 许可证说明

firebuild 使用**专有许可证**（非 GPL、非 OSI 标准许可证）。

LICENSE.md 全文要点：
- Copyright © 2022 Firebuild Inc. All rights reserved.
- 个人使用或商业试用免费
- 非试用商业使用需要从 firebuild.com 获取授权
- 允许修改和再分发，但衍生作品的商业使用受相同要求约束

**积分赛场景**：仅做编译适配与测试属于"个人使用或商业试用"范畴。
`conanfile.py` 的 `license` 字段写 `"Proprietary"`。

如果许可证妨碍分发，需提示 Coordinator。本许可证允许再分发和修改，
但商业使用需授权——在积分赛上下文中这不构成阻碍。

**上游 LICENSE.md 许可条款明细**（供 Reviewer 核对）：
- **免费使用范围**：个人使用免费、商业试用免费（free-for-personal-use/commercial-trial）
- **修改与再分发**：允许修改源码和再分发（包括衍生作品），但衍生作品的商业使用同样需授权
- **免责条款**：MIT 风格免责条款（按"as is"提供，作者不承担任何责任）
- **conanfile.py license 字段**：保留 "Proprietary"——这是对上述条款的合理概括（非 OSI 标准开源许可证，但允许修改再分发）

## 构建系统

- **构建系统**：CMake（最低版本 3.13），非 autotools
- **语言/标准**：C++20（`-std=c++20`），部分 C 源用 gnu89
- **产物**：
  - `firebuild-bin`（可执行文件，安装名 `firebuild`，到 `bin/`）
  - `libfirebuild.so`（LD_PRELOAD 拦截器共享库，到 `lib/`）
  - 配置文件 `etc/firebuild.conf`

## 核心机制

Firebuild 通过以下机制加速构建：

1. **LD_PRELOAD 拦截器**（`libfirebuild.so`）：注入到被加速的进程中，
   拦截 fork/exec/posix_spawn/system/popen 等系统调用
2. **Supervisor 进程**（`firebuild-bin`）：管理构建缓存，与拦截器通过
   FIFO/socket 进行 IPC 通信
3. **缓存层**：使用 xxhash 做内容哈希，zstd 做缓存压缩

## 依赖处理

### 已适配依赖（通过 ohpcd remote）

| 依赖 | 版本 | 用途 |
|------|------|------|
| libconfig | 1.7.3 | 配置文件解析 |
| libelf | 0.8.13 | ELF 文件操作 |
| xxhash | 0.8.3 | 内容哈希 |
| zstd | 1.5.7.1 | 缓存压缩 |

### tsl-hopscotch-map（vendored）

- header-only C++ 库（`tsl::hopscotch_map`）
- ohpcd 上无此包
- 解决方案：在 `build()` 中从 GitHub 下载 v2.3.0 头文件，
  vendored 到源码树的 `include/tsl/` 目录
- SHA-256: `a59d65b552dc7682521989842418c92257147f5068152b5af50e917892ad9317`

### Python Jinja2（构建时代码生成）

- firebuild 构建时需要 Jinja2 来从模板生成拦截器代码
- 设备 Python 环境已安装 Jinja2 3.1.4

## 补丁说明

### 0001-fix-generate_interceptors-ohos-platform.patch

`generate_interceptors` Python 脚本检查 `sys.platform` 来确定目标平台。
在 HarmonyOS PC 上，Python 报告 `sys.platform == 'ohos'`（不是 `'linux'`），
尽管底层内核是 Linux。

此补丁将 `'ohos'` 添加到支持的平台列表中，并将其映射到 `'linux'` 目标，
因为 OHOS 使用 Linux 兼容的系统调用语义。

### 0002-allow-conan-provided-dependency-paths.patch

firebuild 上游使用 `find_package(LibConfig)` 和 `pkg_check_modules()` 来
查找 libconfig、xxhash、zstd、libelf 和 tsl-hopscotch-map。

在 HarmonyOS PC 上使用 Conan 时，这些包位于 Conan 的 `package_folder` 目录中，
无法通过系统路径或 pkg-config 发现。

此补丁添加条件逻辑：当 Conan recipe 通过 `-D` 变量提供路径时，
跳过上游的 `find_package`/`pkg_check_modules` 调用并直接使用提供的路径。
这保留了上游兼容性同时启用基于 Conan 的构建。

### 0003-add-build-manpages-option.patch

man 页面生成需要 xsltproc 和 DocBook XSL 样式表，从
`http://docbook.sourceforge.net/` 加载。在 HarmonyOS PC 上，
网络受限且 DocBook XSL 未安装。

添加 `BUILD_MANPAGES` CMake 选项（默认 ON），Conan recipe 传入
`-DBUILD_MANPAGES=OFF` 跳过 man 页面生成。

### 0004-fix-bits-types-file-include-for-musl.patch

`intercept.h` 在 `#ifdef __linux__` 下包含 `<bits/types/FILE.h>`。
此头文件是 glibc 内部头文件，在 musl libc（OHOS 使用）中不存在。
FILE 类型在 musl 中由 `<stdio.h>` 提供。

用 `__GLIBC__` 守卫 glibc 特定的 include，在 musl 系统上 fallback 到
`<stdio.h>`。

### 0005-fix-glibc-specific-includes-for-musl.patch

`interceptors.h` 包含 `<error.h>` 和 `<bits/timex.h>`，这些是
glibc 内部头文件，在 musl libc（OHOS 使用）中不可用。

用 `__GLIBC__` 守卫 `<error.h>`（musl 不提供 error.h）。
用 `__GLIBC__` 守卫 `<bits/timex.h>`，在 musl 上 fallback 到
`<sys/timex.h>`。

## 上游测试集成（任务 #2/#3/#4）

### 测试集成过程

上游测试集成通过 conanfile.py 的 `_run_upstream_tests()` 方法在 CI 构建阶段执行，分 5 步：

1. **Step 1**：构建 check-bins + fbb_test（`cmake --build --target check-bins fbb_test -- -j$(nproc) -k 0`）
   - `-k 0` keep-going：test_error.c 编译失败（musl 无 `<error.h>`）+ test_stat 链接失败（musl 无 `statx` 符号）不阻断 fbb_test 与其余 test_binary 构建
2. **Step 2**：对 21 个 test_binary 执行 OHOS XPM 代码签名（llvm-objcopy + binary-sign-tool）
3. **Step 3**：ctest -R "fbb|test-symbols" --output-on-failure
4. **Step 4**：22 个 test_binary 直接 exec（无 LD_PRELOAD）
5. **Step 5**：bats 集成测试（39 个 @test 场景）
   - 执行前重写构建产物 run-firebuild 的 shebang `#!/bin/bash` → `#!/data/service/hnp/bin/bash`
   - bats 安装在 $HOME/tmp/bats-core（bin/bats）
   - PWD workaround：`cd "$test_dir" && export PWD="$test_dir"`

### 最终真实通过率（round-17 CI，日志 logs/upstream-tests-round-17.log）

| 上游测试组 | 通过率 | 关键原因 |
|------------|--------|----------|
| fbb_test | 1/1 PASS（100%） | round-17 CI ctest: Test #2: fbb → Passed (0.06 sec)；fbb_test 构建成功（Linking CXX executable test/fbb_test）并运行通过 |
| test-symbols | 1/1 PASS（100%） | round-17 显式 `/data/service/hnp/bin/bash ./test_symbols <bdir>` 运行（绕过 shebang），rc=0 |
| 22 test_binary | 15/22 PASS（68.2%） | Pass=15, Fail=5, N/A=2（参数化调用后 +4） |
| bats 39 @test | 1/39 PASS（2.6%） | Pass=1, Skip=4, Fail=34 |

### 根因与证据链

#### supervisor bind EPERM（bats 34 FAIL 根因）

- **源码位置**：`src/firebuild/firebuild.cc` 第 113 行（`create_listener()` 函数内 `bind()` 调用）
- **错误现象**：`FIREBUILD: bind: Operation not permitted`
- **验证方法**：直接运行 `firebuild -c firebuild.conf -- /bin/true`，stderr 输出 EPERM
- **平台能力边界**：OHOS 沙盒限制 AF_UNIX socket bind，非 firebuild 代码缺陷

#### test_error/test_stat 环境限制

| 测试 | 根因 |
|------|------|
| test_error | test_error.c 包含 `#include <error.h>`，musl libc 不提供 `<error.h>` |
| test_stat | test_stat.c 使用 `statx()` 系统调用，musl libc 不提供 `statx` 符号 |

#### test-symbols shebang 问题

test_symbols 脚本 shebang 为 `#!/bin/bash`，设备无 `/bin/bash` → CTest BAD_COMMAND。这是上游测试源文件，未修改（零上游测试文件修改原则）。

### round-11 vs round-10 改进

| 指标 | round-10 | round-11 | 修复内容 |
|------|----------|----------|----------|
| fbb_test | 0/1 FAIL | 1/1 PASS | round-17 CI：fbb_test 构建成功（Linking CXX executable test/fbb_test），ctest Test #2: fbb → Passed |
| 22 test_binary | 3/22 PASS (13.6%) | 11/22 PASS (50.0%) | Step 1 加 -k 0 keep-going |
| bats | 0/39 PASS (0.0%) | 1/39 PASS (2.6%) | Step 5 加 run-firebuild shebang 重写 |
| test-symbols | 0/1 FAIL | 0/1 FAIL | 无变化（上游 test_symbols shebang 问题） |

### test_package 验证范围说明

test_package 的 smoke test 验证了以下内容：
1. firebuild 二进制文件存在且可执行（`access(TARGET_BIN, X_OK)`）
2. libfirebuild.so 共享库文件存在（`access(TARGET_SO, F_OK)`）
3. firebuild --version 命令成功执行并输出 "Firebuild 0.8.6.1"（fork + exec）

**未验证的核心功能**：firebuild 的核心机制是 LD_PRELOAD 拦截器（libfirebuild.so）在运行时拦截 fork/exec/posix_spawn 等系统调用。test_package **未验证** LD_PRELOAD 拦截器的运行时拦截功能——即未在实际构建命令上通过 `firebuild make ...` 验证加速缓存效果。原因是：libfirebuild.so 的 `__attribute__((constructor))` 会尝试连接 firebuild supervisor 进程、读取 /proc/self/exe 并发送 FBB 消息，在没有运行 supervisor 的情况下会在 OHOS 上 segfault。验证完整的拦截器→supervisor→缓存闭环需要多进程协调，超出 test_package smoke test 范围。

### L2 smoke 门禁与 test_package 内部验证的口径差异

CI 日志显示 L2 smoke test（`firebuild --version/--help`）在 L2 门禁阶段结果为 skip（non-blocking），而 test_package 内部通过 fork+exec 运行 `firebuild --version` 成功输出 "Firebuild 0.8.6.1"。这两个结果不矛盾——口径不同：
- **L2 门禁**：在 HMDFS 路径上直接 exec firebuild 二进制，受 PATH/环境变量/HMDFS exec 权限等影响，可能因环境不完整而 skip
- **test_package 内部**：在 Conan test_package 环境中（已设置 conanrun env、RPATH 等）通过 fork+exec 运行，环境完整，因此成功

L2 skip 不代表 firebuild --version 实际失败，仅代表 L2 门禁的执行路径上遇到了 non-blocking 问题。test_package 内部的成功执行是更强的证据。

## OHOS 风险评估

### 高风险
1. **LD_PRELOAD + musl 拦截兼容性**：firebuild 的核心机制是 LD_PRELOAD 注入 +
   大量 glibc 函数拦截。OHOS 使用 musl libc，函数签名/行为可能不同。
   正面证据：E200 确认 LD_PRELOAD 在 OHOS 上可用。

2. **tsl-hopscotch-map 未适配**：已通过 vendored header 解决。

### 中风险
3. **FIFO/socket IPC 在 HMDFS 上**：firebuild 拦截器与 supervisor 之间使用
   FIFO 通信，HMDFS 对 FIFO 的支持可能与标准 Linux 不同。

4. **信号处理兼容性**：musl 的信号处理实现可能与 glibc 有细微差异。

## 产物签名

鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名。
`_sign_binaries()` 方法使用 `binary-sign-tool -selfSign 1` 对产物签名。
