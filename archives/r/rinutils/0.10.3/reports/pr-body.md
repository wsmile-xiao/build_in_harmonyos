# 【积分赛】rinutils 0.10.3 适配鸿蒙 PC

## 三方库信息

- **三方库名称**：rinutils
- **上游版本**：0.10.3
- **上游仓库地址**：https://github.com/shlomif/rinutils
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无既有条目命中（知识图谱无 header-only/CMake 专项条目）；本次沉淀 `knowledge_gained` 4 条（见 `manifest.yaml`），并留有语言预检反证与同型先例记录（`notes.md`）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 8 | 来源：`t/`（1×C/cmocka `bit-reader-and-writer-test.c` + 7×Perl `.t`，其中 4 个经 `Inline::C` 现场编译 C 片段） |
| 集成测试 | 0 | 上游无独立集成测试 |
| 其他测试 | 1 | `run-tests.pl`（`prove` 运行器，非独立用例，不计入合计） |
| **合计** | **8** | |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 1 | 可运行面上游用例 1/1（100%） | 上游 C/cmocka 用例经 `conan create` 的 `build()` 真实编译执行（6 断言全过）；7 个 Perl 用例依赖 CPAN `Inline::C` 工具链，OHOS 不可运行（逐项技术原因见 `notes.md` §上游测试清点） |
| 集成测试 | 0 | 不变 | 上游无 |
| 鸿蒙特有测试 | 1（36 断言） | 新增 | `test_package/` 消费者测试：13 个安装头文件全部编译消费、其中 12 个含运行时断言（含负向用例），经 `find_package(Rinutils)` + `Rinutils::Rinutils` 消费 |
| **合计** | **2（36 断言）** | **新增 1 个鸿蒙消费者测试** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] 是，存在对上游测试用例的修改（请在下方逐条说明）

> 上游 `t/` 下 8 个测试文件与 `run-tests.pl` 均未改动；`conandata.yml` 补丁只涉及构建可复现性（见下），不含任何测试文件。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（可运行面已全部真实执行）
- [ ] 是，上游无测试用例，适配后补全了测试

> 上游已有测试；本适配额外新增鸿蒙消费者测试（非替代）：
> - **补全范围**：`test_package/test.c`，36 项运行时断言覆盖 13 个头文件（COUNT/LAST、min/max、字符串工具、alloc 包装、bit 读写器往返/覆盖/跳过、`RIN_LL_FMT`/`RIN_LL9_FMT`、`portable_time`、`likely`/`typeof_wrap`/`GCC_UNUSED`/`DLLEXPORT`），含负向用例；`exit_error.h` 为 compile-only（`noreturn` 语义无法进程内断言）。
> - **原因**：上游 7 个 Perl 用例在 OHOS 无 CPAN Inline::C 运行环境；消费者视角验证同时证明安装产物（头文件 + pc + CMake 配置）可被真实消费。
> - **文件**：`archives/r/rinutils/0.10.3/test_package/{test.c,CMakeLists.txt,conanfile.py,MANIFEST.yml}`。

## 验证结果

- 编译状态：**通过**（`conan-verify` G0–G4 + L2/L4/L5 全过；本地 CI 门禁 L0/L1/L1e/L2/L4/L5 全过）
- 上游测试用例通过率：**1/1（100%）**（可运行面；7 个 Perl 用例不可运行原因逐项列明于 `notes.md`，未伪造结果）
- 新增测试用例通过率：**36/36（100%）**（`conan create` 内 ctest 1/1 Passed + 直接运行输出 `ALL 36 CHECKS PASSED`）

## 补充说明

1. **构建可复现性（2 个补丁，无平台宏）**：上游 `cmake/shlomif_common_bootstrap.cmake` 会在 configure 期从 GitHub `FILE(DOWNLOAD)` 拉取 `Shlomif_Common.cmake`，且该模块无条件 `FATAL_ERROR` 要求 perl。适配内置该模块的裁剪副本（仅保留 CMakeLists 实际使用的 4 个宏，保留 MIT 版权），并把下载分支改为 `FATAL_ERROR`——configure 完全离线，且不再依赖本构建用不到的 perl。
2. **源码 URL**：`github.com/archive` 的 302 目标是 GitHub 官方 tar 入口 `codeload.github.com`（仓库内 284 个既有配方同源），设备/CI 均无法直连 `github.com`；sha256 已与 `github.com/archive` 下载件二次核对一致。
3. **R47 语言预检误报已留证**：检具把 Perl 测试/CI 脚手架计入主体判 `mixed`（交付物实为 CMake 安装的 14 个 C 头文件）；按 libemf/libcaca/cronic 同型先例以反证复核后继续，未伪造 `detected_language` 字段，自动写入的 `env_unsupported` 终态已更正为进行中草稿（详见 `notes.md`）。
4. **上游 C 用例执行方式**：上游 CMake 只把 perl 运行器注册进 CTest，cmocka 用例由 `run-tests.pl` 以 `t/*.t.exe` glob 收集，故配方在 `build()` 中直接执行 `bit-reader-and-writer-test.t.exe`（失败即 `conan create` 失败）。
5. **已知限制**：7 个 Perl 用例（4 个 `Inline::C` 现场编译、1 个完整打包流程、2 个代码风格）依赖 OHOS 不提供的 CPAN 模块（无 cpanm，逐项模块探测见 `notes.md`）；HMDFS 不允许 mkfifo，gmake jobserver 警告后自动降级为串行，无功能影响。
6. **消费者接入**：CMake `find_package(Rinutils)` → `Rinutils::Rinutils`；pkg-config 文件为 `librinutils.pc`。`rin_cmocka.h` 需外部 cmocka 头，仅测试场景使用。
