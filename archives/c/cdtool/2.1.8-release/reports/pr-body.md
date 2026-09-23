## PR 信息

- **三方库名称**：cdtool
- **上游版本**：2.1.8（上游官网最新发布版，2006-08-09；任务卡版本串 `2.1.8-release` 的来源见补充说明）
- **上游仓库地址**：https://hinterhof.net/cdtool/
- **适配路径**：路径 A（基础适配）
- **使用知识库**：无（仅引用知识图谱既有条目 E011）

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游 tarball 顶层无 `tests/` 目录（顶层 39 个条目全为源文件/文档/手册页） |
| 集成测试 | 0 | 无测试框架 |
| 其他测试 | 0 | `Makefile.in` 无 check/test 目标（实跑零命中）；`configure.ac` 无测试宏（实跑零命中，全文 88 行） |
| **合计** | **0** | 上游无自动化测试，如实声明 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | 上游无单元测试 |
| 集成测试 | 0 | 不变 | 上游无集成测试 |
| 鸿蒙特有测试 | 16 | 新增 | `test_package/test_cdtool.py` 消费者测试：安装布局与产物完整性 9 项、OHOS 产物属性 3 项、5 个已安装命令真实运行，共 16 条断言（消费者断言计 16） |
| **合计** | **16** | **+16** | 上游 0 + 鸿蒙特有测试 16 |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 上游未提供任何测试套件，本次未改动上游任何测试代码或断言。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，上游无测试用例，适配后补全了测试（请在下方说明）

> - **补全的测试范围**：为已安装产物补全消费者侧验证——安装布局（主程序、别名符号链接、独立产物、手册页）、OHOS 产物属性（架构/PIE/musl 加载器/不依赖 glibc）、以及 5 个命令的真实运行；另在构建期对 4 个刚构建二进制做 `-V`/`-h` 冒烟作为功能性替代验证
> - **补全原因**：上游仅有源文件与 Makefile，无正式测试框架，无法给出上游通过率
> - **新增测试文件清单**：
>   1. `test_package/conanfile.py` — 消费测试入口，声明 `layout()` 并直跑校验脚本
>   2. `test_package/test_cdtool.py` — 16 条断言的消费者校验脚本
>   3. `test_package/MANIFEST.yml` — 上游测试审计与消费者用例声明

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：0/0（不适用——上游 0 个可运行测试入口）
- 新增测试用例通过率：16/16（100%）

## 文件改动记录

| 路径 | 说明 |
|------|------|
| `archives/c/cdtool/2.1.8-release/conanfile.py` | Conan 配方（`package_type=application`，零第三方依赖） |
| `archives/c/cdtool/2.1.8-release/conandata.yml` | 源码 URL + sha256 + 3 个补丁声明 |
| `archives/c/cdtool/2.1.8-release/patches/0001-configure-umask-000.patch` | `configure` 中两处 `umask 077` → `umask 000` |
| `archives/c/cdtool/2.1.8-release/patches/0002-commands-include-fcntl.patch` | `commands.c` 补 `#include <fcntl.h>` |
| `archives/c/cdtool/2.1.8-release/patches/0003-cdown-getline-rename.patch` | `cdown.c` 自定义 `getline` 改名 `cdtool_getline` |
| `archives/c/cdtool/2.1.8-release/test_package/` | 消费测试（`conanfile.py` + `test_cdtool.py` + `MANIFEST.yml`） |
| `archives/c/cdtool/2.1.8-release/manifest.yaml` | 版本级 manifest |
| `archives/c/cdtool/manifest.yaml` | 软件级 manifest |
| `archives/c/cdtool/commands.json` | 命令行工具声明（`type=tool`） |
| `archives/c/cdtool/2.1.8-release/notes.md` | 适配笔记（错误依据、补丁表、布局、未覆盖范围） |
| `archives/c/cdtool/2.1.8-release/reports/` | 逐字构建日志、W3 本地 CI 模拟日志、门禁报告、人工补测报告、PR 正文 |

## 补充说明

**命名与版本串来源**：上游项目名、Debian 包名与平台任务卡软件名均为单数 `cdtool`。版本串 `2.1.8-release` 取自 Debian 上游版本号（`cdtool_2.1.8-release-9.dsc` 的 `Version: 2.1.8-release-9`），其 orig tarball 与官网 `cdtool-2.1.8.tar.gz` 的 sha256 逐字节相同。目录与配方版本保持任务卡值，以满足 CI 分支名门禁（分支去前缀与「包目录名-版本」精确匹配）。

**源码来源与校验和**：官方源 `https://hinterhof.net/cdtool/dist/cdtool-2.1.8.tar.gz`（HTTP 302 跳 HTTPS，最终 200），sha256 `73de81ea2de2eae64b888e1b2739ef643ccea13c79790569f8e6278369976a21`，116847 字节，与配方声明一致。

**源码修改（3 个补丁，全部由设备上第一条真实错误驱动）**：

1. `0001`：autoconf 生成的 `configure` 用 `umask 077` 建 `config.status` 临时目录，OHOS 上 0700 目录对构建进程不可写，`config.status` 重定向全部 `Permission denied`，`config.h`/`Makefile` 未生成；**`configure` 自身仍返回 0（静默失败）**，错误推迟到 `make` 才以 `No targets specified and no makefile found` 暴露（知识图谱 E011）。改为 `umask 000`。
2. `0002`：`commands.c` 使用 `O_RDONLY | O_NONBLOCK` 但未包含 `fcntl.h`；其已包含的 `sys/file.h` 在 OHOS musl 上不引入 `fcntl.h`，clang 15 报 `use of undeclared identifier 'O_RDONLY'`。补 `#include <fcntl.h>`。
3. `0003`：`cdown.c` 自定义 `char *getline(void)` 与 musl `stdio.h` 声明的 POSIX.1-2008 `ssize_t getline(char**, size_t*, FILE*)` 冲突，报 `conflicting types for 'getline'` 与全部调用点 `too few arguments`。将定义、13 处引用与注释统一改名为 `cdtool_getline`。

**安装布局（上游单程序多名字设计）**：主程序装在 `lib/cdtool/cdtool`，`bin/` 下 10 个别名是相对符号链接 `../lib/cdtool/cdtool`（argv[0] 分派），另有 `cdctrl`/`cdown`/`cdadd`/`cdloop`/`cdtool2cddb` 五个独立产物；`share/man/man1` 下 16 份手册页。`bin/` 下没有名为 `cdtool` 的入口，`package_info()` 已按真实产物声明。

**依赖**：零第三方 Conan 依赖（socket 由 libc 提供，`getopt.h`/`mntent.h`/`linux/cdrom.h` 由 OHOS sysroot 提供）。

**未覆盖范围（如实声明）**：cdtool 的核心功能是 CD-ROM 音频控制（`CDROMPLAYMSF`/`CDROMSTOP`/`CDROMEJECT` 等 ioctl），运行需要真实光驱，OHOS PC 设备无光驱，因此播放/停止/弹出/音量等核心路径**无真机验证**；已有验证只覆盖安装布局、产物属性与版本/用法早退分支。

**产物不可完全复现的说明**：上游在 4 处调用点把 `__DATE__`/`__TIME__` 写进版本横幅（`cdctrl.c:72,112`、`cdown.c:725`、`cdtool.c:218`），故 `lib/cdtool/cdtool`、`bin/cdctrl`、`bin/cdown` 三个产物跨轮 sha256 不同；`bin/cdtool2cddb`、两个 shell 脚本与全部符号链接逐字节一致。基线只对可复现子集给出，详见 `reports/conan-verify-supplement.md`。

**证据索引**：`reports/conan-create-log.md`（逐字构建日志，含 3 条 `Apply patch` 与消费者测试段）、`reports/w3-local-ci-log.md`（W3 本地 CI 模拟逐字日志，消费者 16 条断言全 PASS）、`reports/conan-verify-report.md`（门禁报告）、`reports/conan-verify-supplement.md`（纯可执行包 G4/L2/L4/L5 人工补测 + 可复现性根因）。

**建 PR 前置门禁绕行留痕（`--no-preflight`，确定性误报）**：`gitcode_pr.py create-pr` 的 PF0 把 `--target` 的值**同时**用作 PR base 与本地 diff 基线；本 worktree 的本地 `main` 是用户 fork 的旧基线（`7c11b6c082`，落后 `upstream/main` 1803 个提交），以它为基线 diff 得到 11344 个文件，且 PF 链路会在这些无关文件上长时间无输出。故本轮改为以 `upstream/main` 为基线**本地等价执行** PF1-PF4：单包原子性、无二进制条目、test_package 实质、依赖在仓——**四项全部通过**（无任何 finding）。唯一未通过项是 **PF9**：该闸要求所有 `archives/` 变更路径深度 ≥5，而 `archives/<字母>/<包>/commands.json`（软件级命令行声明，CI L0k 强制要求）与 `archives/<字母>/<包>/manifest.yaml`（软件级 manifest，仓库现有 3031 份）深度为 4。这两个文件是仓库规范要求，不能为迁就该闸而删除，故按「PF0/PF8/PF9 确定性误报可 `--no-preflight`」口径建 PR 并在此留痕。

**W4 审计 delta 声明（T1）**：W4 独立审计 `verdict=pass`、P0=0、P1=0，结论 `head_sha=710cb08c3274dda13b8efc461dfe35a8eef371b2`；其后 delta 仅含 `reports/pr-body.md`（即本段留痕），不涉及 `conanfile.py`/`conandata.yml`/`patches/`/`test_package/` 等构建输入，也未改门禁物料，已按文档一致性口径自检。
