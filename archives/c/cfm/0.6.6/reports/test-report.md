# cfm 0.6.6 - 测试报告

> **测试日期**: 2026-09-20
> **测试环境**: HarmonyOS PC (aarch64), clang 15.0.4 (aarch64-unknown-linux-ohos)
> **构建方式**: conan create (ohos-aarch64 profile) + 消费者用例

## 上游测试枚举台账（完整枚举）

官方 tag v0.6.6 tarball（https://github.com/sophec/cfm/archive/refs/tags/v0.6.6.tar.gz,
SHA-256 7977431d8074d3a2f0dad4e431e558201073631fa5f0e7d92b37b100feae6ed3）
完整文件清单（tar tzf 枚举）：

| 文件 | 类别 | 是否独立上游用例 | 说明 |
|------|------|------------------|------|
| cfm.c | 用户测试源/主程序 | 否 | 单一 C 源文件（约 2000 行 TUI 实现），无 TEST_CASE/断言框架 |
| config.def.h | 框架配置头 | 否 | 配置模板，非测试 |
| Makefile | 构建目标 | 否 | 仅 all/install/uninstall/clean，**无 check 目标**（`make check` → No rule） |
| cfm.1 | 手册 | 否 | man page |
| README.md | 文档 | 否 | 文档 |
| LICENSE | 文档 | 否 | MPL-2.0 |
| .gitignore / .github/workflows/cbuild.yml | 构建脚本 | 否 | CI 工作流（构建 cfm 仅验证编译） |
| screenshot.png | 素材 | 否 | 截图 |
| tests/ 目录 | 测试源 | 不存在 | 无 tests/、test/、unittests/ 目录 |
| 基准/样例/fixture | 测试数据 | 不存在 | 无 |

**结论：上游独立测试用例数 = 0**（source_declared_total=0）。cfm 上游不提供任何测试框架、
测试声明或 check 目标；`make check` 实测报 "No rule to make target 'check'"。

## 双口径统计

| 口径 | 数值 |
|------|------|
| source_declared_total（官方源码声明测试总数） | 0 |
| configured_executable_total（当前 OHOS 配置实际可执行用例） | 0（上游） |
| 新增 HarmonyOS 专项/消费者用例 | 2（下述） |
| executed_passed_total（新增用例） | 2/2 |

> 上游 0/0，无未实例化项。新增用例不计入上游口径，单独列示（防重复充数）。

## 新增测试用例（HarmonyOS 专项 + 消费者）

### 用例 1：消费者 C 用例（test_package/test.c）
- **源文件**: archives/c/cfm/0.6.6/test_package/test.c
- **构建命令**: `/data/service/hnp/bin/clang test.c -o consumer_test`（conan test_package build()）
- **cwd**: archives/c/cfm/0.6.6/test_package
- **运行命令**: `./consumer_test`（fork+execvp("cfm", <mkdtemp scratch>)，stdin 关闭）
- **退出码**: 0
- **验证结果**: PASS: cfm binary launched and exited cleanly (rc=0)

### 用例 2：消费者 pty TUI 用例（test_package/conanfile.py test()）
- **运行命令**: conan test() 内 pty.fork() 启动 `cfm <mkdtemp dir>`
- **cwd**: archives/c/cfm/0.6.6/test_package
- **退出码**: 0（发送 'q' 干净退出）
- **验证结果**: PASS: cfm consumer: pty TUI rendered (226 bytes), quit rc=0
  （断言输出含 \x1b[ 转义序列 = 备屏渲染成功）

### 用例 3：非交互冒烟（conan test() 内）
- **运行命令**: `cfm <tmpdir> </dev/null >/dev/null 2>&1`
- **退出码**: 0（目录扫描 + 干净退出）

## 构建与门禁结论

| 门禁 | 结果 |
|------|------|
| W3 conan create（ohos-aarch64 profile） | ✅ PASS（含 test_package 全量执行） |
| conan-verify G0-G4 + L2/L4/L5 | ✅ PASS |
| L2 smoke（--version/--help） | ⚠️ warn：cfm 无 --version/--help 参数（argc==1 视为目录），L2 判 warn 非阻塞 |
| W2/W3 基线隔离复验 | ✅ PASS（见 notes.md：cloog/kics 预存基线空文件临时隔离→复跑→恢复，pre/post SHA-256 均为 e3b0c442…） |

## 备注

- cfm 为 TUI 交互应用，普通非 TTY 运行（stdin 关闭）快速退出 0，可作为冒烟；
  pty 驱动可完整验证 TUI 渲染与退出（替代 --version 冒烟）。
