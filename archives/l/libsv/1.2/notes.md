# libsv 1.2 适配笔记

> 分支: feat/libsv-1.2-codex
> 更新: 2026-09-27（Conan 化前置适配）

## 一、基本信息

| 项目 | 值 |
|------|-----|
| 软件 | libsv（uael/sv） |
| 版本 | 1.2（tag v1.2） |
| 许可证 | Unlicense（公共领域） |
| 语言/标准 | 纯 C99，无外部依赖 |
| 构建系统 | CMake（另带 autotools/xmake，未使用） |
| 上游 | https://github.com/uael/sv |
| 源码归档 | https://github.com/uael/sv/archive/refs/tags/v1.2.tar.gz |
| SHA256 | `003ca74f3485fd1a4ab809413b1765b91d4314355d244264c98546ad2556cc99` |
| 交付物 | libsv.so（VERSION 1.0.0 / SOVERSION 1）、include/sv/semver.h、lib/pkgconfig/libsv.pc |

## 二、W0 依赖检查结论

```text
依赖数量：0（运行时/构建时/测试时均无外部依赖，纯 libc）
已满足依赖：无需求
缺失依赖：无
是否需要拆分依赖适配：否
阻塞点：无
下一步：直接 Conan 化
```

说明：CMakeLists.txt 的 `project_dependency()` 机制存在，但仓库内无
`cmake/dependencies.cmake`，实际不拉取任何 vendor 依赖。

## 三、W1 源码与构建分析

- 入口 `CMakeLists.txt`：`project(sv C)`，C99；`BUILD_SHARED_LIBS` 默认 ON。
- 源码 `src/*.c`（8 个 .c），公共头 `include/semver.h`（安装到 `include/sv/`）。
- 安装规则：`install(TARGETS sv ...)` + `PUBLIC_HEADER` → `include/sv/semver.h`；
  `scripts/libsv.pc.in` 生成 pkg-config 文件。
- 编译选项：非 MSVC 下 `-Wall -Werror -Wextra -fomit-frame-pointer`
  （OHOS clang 下已验证可通过，见下）。
- 编译器白名单：Clang/GNU/Intel/MSVC，OHOS clang 命中 Clang 分支。

### 上游测试清点（R51 申报表）

| 测试程序 | 源文件 | 用例/调用点 | 说明 |
|---------|--------|------------|------|
| test_version | test/version.c | 49 | 解析/写回/非法输入 |
| test_comp | test/comp.c | 77 | 比较器解析/写回/失败 |
| test_range | test/range.c | 34 | x-range/hyphen/tilde |
| test_match | test/match.c | 93 | 匹配语义 |
| test_utils | test/utils.c | ~6 | 工具函数 |
| test_usage | test/usage.c | 7 asserts | 端到端场景 |
| test_semvers | test/semvers.c | 12 输入场景 | 向量操作 |
| **合计** | **7 个 ctest 程序** | **约 270+ 断言调用点** | |

- 测试仅在顶层构建（`${PROJECT_NAME}_DEVEL`）时注册，Conan 构建即顶层，可用 ctest 执行。
- `test/CMakeLists.txt` 未被主 CMakeLists include（主文件用 glob 直接注册），属上游遗留。

### 已知怪癖（不阻塞）

1. `cmake/properties.cmake` 中版本为 1.0.0，未随 tag v1.2 递增 →
   产物 `libsv.so.1.0.0`、libsv.pc Version=1.0.0。上游一贯如此，不修改。
2. 主 CMakeLists 使用 `block()/endblock()`（需 CMake ≥ 3.25）→
   本机 3.28.2 通过；worker 为 CMake 4，满足要求。
3. `test_usage` 用 `assert()`，Release（NDEBUG）下编译为空操作 —— 上游设计，如实记录。

## 四、Conan 配方说明

- `conanfile.py`：Conan 2 API；`cmake_layout` + `CMakeToolchain`；
  build() 内执行上游 ctest（期望 7 通过），输出 `HMBS_UPSTREAM_TEST_RESULT=`
  JSON 证据标记（同 lasi/1.1.3 模式）。ctest 通过 build() 生成的包装脚本
  运行（脚本内部 export LD_LIBRARY_PATH=<cmake_layout 的 build_folder>，
  因 OHOS 构建树产物无 rpath、且 conan 的环境管理会剥离命令级变量前缀）；
  上游测试执行用 `cross_building(self)` 守卫：真机/CI 为 OHOS 原生构建
  （非交叉）时完整执行；纯交叉宿主（如本机 Windows）只编译不运行。
  注意：OHOS 适配版 conan（2.29.1）的 `ConanFile` 无 `can_run()`，
  必须用 `conan.tools.build.cross_building`。
- OHOS 处理：适配版 conan 自动将 OHOS 映射为 CMAKE_SYSTEM_NAME=
  HarmonyOS 并注入工具链环境，配方不做任何平台别名（lasi/1.1.3 时代的
  `Linux` 别名是旧 workaround，实测会绕开 conan 的 OHOS 处理链，已移除）。
- 无补丁：纯 C99 库 OHOS 直接可编，`patches: []`。
- `package_info`：`libs=["sv"]`，CMake 目标 `libsv::libsv`，pkg-config 名 `libsv`。
- 版本号：制品仓尚无 libsv/1.2（v2 revisions API 探测 404 + 真机 L0j
  "version not in registry yet"），首次适配用上游原版 `1.2`。
- test_package：`test_sv.c` 26 个 CHECK 断言，全部取自上游已验证用例；
  运行用 `env="conanrun"`（提供 package 目录 lib 的 LD_LIBRARY_PATH），
  交叉构建守卫跳过运行（不影响真机原生执行）。

## 五、本机验证记录（2026-09-27，Windows + DevEco OHOS SDK 交叉验证）

静态检查：
- `git diff --check`：通过。
- `python -m py_compile`：conanfile.py ×2 通过。
- YAML 解析：conandata.yml / manifest.yaml / MANIFEST.yml 通过。
- `conan export`（OHOS 适配版 conan 2.29.1）：配方加载导出成功。

源码级 OHOS aarch64 交叉编译（DevEco SDK clang 15 + ohos.toolchain.cmake）：
- 库与 7 个上游测试程序全部编译链接通过（产物为 aarch64 musl ELF）。
- 注：sv 自带 `-Wall -Werror -Wextra`；Windows 宿主的 OHOS 工具链会注入
  `--gcc-toolchain` 驱动参数（宿主上 unused），被 -Werror 误杀。本机验证时
  以 `-Wno-error=unused-command-line-argument` 降级该驱动警告后源码零告警
  通过。真机 conan 工具链不注入该参数，2026-06-12 手工编译亦通过，无此问题。
- 消费者视角：test_package/test_sv.c 以 `-I<prefix>/include -L<prefix>/lib -lsv`
  交叉编译链接成功（aarch64 musl ELF）。

完整 conan create 流水线（本机模拟 OHOS 交叉）：
- venv 安装 OHOS 适配版 conan 2.29.1（社区 PyPI wheel + 公共 PyPI 依赖）。
- host profile: os=OHOS/arch=armv8/clang 15，编译器经 wrapper 注入
  `--target=aarch64-linux-ohos --sysroot=<DevEco sysroot>`；
  build profile: Windows；generator=Ninja。
- 源码 URL 临时改为 `file://`（本机 github.com 不可达，等同 CI predownload
  机制），sha256 校验通过；仓库内 conandata.yml 保持官方 URL。
- 结果：export ✓ → source ✓ → 编译 ✓ → package ✓（include/sv/semver.h、
  lib/libsv.so*、lib/pkgconfig/libsv.pc、licenses/UNLICENSE）→
  test_package CMakeDeps 消费编译链接 ✓（日志含 "Target declared 'libsv::libsv'"）。
- 未在本机执行：上游 ctest 与 test_sv 运行（交叉产物无法在 Windows 执行），
  已由 cross_building 守卫按设计跳过——待真机/shadow CI 回填 7/7 与 26 断言结果。

## 六、真机 shadow CI 记录（2026-09-27）

设备：HarmonyOS PC（HongMeng Kernel 1.12.0, aarch64），job
`libsv-1.2-20260927`（repo-source 取自 qtnetworkauth job，`--mode heavy`
自动全局锁排队）。

### 迭代记录

| 项 | r1 | r2 | r3 | r4 | r5 | r6 |
|----|----|----|----|----|----|----|
| run 目录 | …-145059-1930 | …-145424-3929 | …-145903-10207 | …-150037-11426 | …-150256-14606 | …-150753-25974 |
| 排队 wait_seconds | 0 | 0 | 0 | 0 | 0 | 106 |
| exit code | 1 | 1 | 1 | 1 | 1 | **0** |
| L0 / L1 / L2 / L4 / L5 | L0=pass / L1=fail / 其余 skip | 同 | 同 | 同 | 同 | **全 pass（L2=skip: no bin/）** |
| 报错原文 | `cmake: inaccessible or not found`（127） | 同 | `Error loading shared library libsv.so`，ctest 0/7 | 同 r3 | 同 r3 | — |
| 根因 | 启动会话 PATH 缺工具链目录（r1 误判为 CMAKE_SYSTEM_NAME，r2 证伪） | 同 | 无 rpath + musl 加载器找不到库 | 同 | lib_dir 拼错路径（cmake_layout 的 build_folder 本身就是 build/Release） | — |
| 解法 | — | 删 Linux 别名（化简） | PATH 前缀（编译 100%） | — | — | lib_dir=self.build_folder + 兜底探测 |

### r6 最终结果（全绿）

```text
exit_code:            0
排队 wait_seconds:    106
上游测试:             100% tests passed, 7/7（HMBS_UPSTREAM_TEST_RESULT:
                      passed, executed=7, passed=7, failed=0, skipped=0）
test_package:         ctest 1/1 Passed + 直接运行 ./test_sv → 26 checks, 0 failures
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir   （纯库，正常）
L4_RESULT=pass: no patches
L5_RESULT=pass: lib/ has content
Build Summary:        Success 1 / Failed 0
```

**关键实证（r4 后设备手动实验）**：
1. `LD_LIBRARY_PATH=<build>/build/Release ctest --test-dir <build>/build/Release --output-on-failure`
   在真机手动执行 → **100% tests passed, 7/7**（上游测试真机全绿的直接证据）。
2. 直接运行单个测试程序（HMDFS 上）同样成功——排除 HMDFS 执行/签名问题。
3. 同样的前缀写进 conan `self.run()` 命令字符串则无效——conan 的环境管理
   （[buildenv] 注册 LD_LIBRARY_PATH 同名变量）覆盖了 shell 级前缀。

**真实根因（r1/r2 归纳）**：两轮均在 build() 的 `cmake.configure()` 处 exit 127
（cmake 不可达）。L0 门禁全过、镜像 fallback 下载源码成功、conan export
正常。设备上 cmake/ninja/make 实际位于 `/data/service/hnp/bin`（cmake 4.1.2，
直接路径调用正常），但 runner 继承的启动会话 PATH 不含该目录；ci profile
`[buildenv]` 中的 `PATH=+(path)/data/service/hnp/bin` 是 OHOS 适配版 conan
的专属语法，在当前 job 环境调用的 conan 上未生效（PATH 未被注入）。对照
同日成功的 libuinputplus/0.1.4 job：同 profile、同 env.txt PATH、无
tool_requires，其 cmake 却执行成功——说明其**启动会话**携带了工具链 PATH
（会话间环境差异），而非 conan 机制差异。

r2 曾按 r1 假设移除 `CMAKE_SYSTEM_NAME=Linux` 旧 workaround（lasi/1.1.3 时
代做法）——未解决问题，但该清理本身正确：适配版 conan 会自动映射
HarmonyOS，别名反而绕开其 OHOS 处理；本机交叉复验通过后保留此简化。

**r3 修复**：启动 runner 时显式前缀工具链 PATH（环境组装，不绕过锁，
runner 照常 `--mode heavy` 排队）：

```sh
ssh <device> 'PATH=/data/service/hnp/bin:$PATH \
  sh ~/ohos-users/codex/libsv-1.2-20260927/run-conan-heavy.sh'
```

> ⚠️ 共性提示（后续库 shadow CI 适用）：凡 conan 配方在真机上调
> cmake/ninja/make 报 `inaccessible or not found`（exit 127），优先检查
> 启动会话是否携带 `/data/service/hnp/bin`，而非先改配方。

### 下一步命令（job 已就位）

```sh
sh "$HOME/ohos-users/codex/libsv-1.2-20260927/run-conan-heavy.sh"
```


## 七、历史记录（2026-06-12 手工编译，保留）

```text
编译步骤:
1. cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local
2. make && make install
交付物:
- 动态库: libsv.so
- 头文件: sv/semver.h
```
