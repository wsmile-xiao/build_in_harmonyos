# ondir 0.2.3 鸿蒙 PC 适配笔记

## 状态（2026-09-10）

- conan create: **PASS**（W3 本地 CI 通过，含 test_package 全部断言）
- 上游自动化测试: **无**（上游 0.2.3 不提供任何测试套件，见下"上游测试评估"）
- 版本来源: 上游发布提交 `cb2f9f8b21e336165fc0a310d677fda75c8e8513`
  （"Release 0.2.3.", 2013-09-19）。**该仓库没有 git tag**，因此发布提交
  是唯一权威来源（R39 官方 codeload 归档）。

## 编译环境

- 构建系统: makefile（手写 Makefile，无 autoconf/configure）
- 编译日期: 2026-09-10
- 编译器: clang 15（OHOS musl 工具链）
- 状态: built
- 依赖: 无（仅 POSIX regex.h / sys/stat.h / unistd.h getcwd）

## 适配对话记录

### 对话 #1（2026-09-10，主任务派发 + W1）
任务：按 `openharmony-compile-agent` SKILL 端到端适配 ondir 0.2.3 到
HarmonyOS PC（aarch64-linux-ohos, musl, clang 15）并提 PR。
W1：`git fetch upstream` → 从 `upstream/main`（1f6f17ddab）切出
`feat/ondir-0.2.3`；工作区既有脏文件 `archives/l/libxext/{README.md,manifest.yaml}`
按要求原样保留、未触碰。

### 对话 #2（2026-09-10，源码核验 + R47）
codeload 官方源下载 `ondir-0.2.3.tar.gz`，实测 sha256
`447f3d9e…c1235a569565732` 与预期一致。解压确认 19 个文件，
**确认 0.2.3 没有 `ondir_prompt_hook.fish`**（该文件是 0.2.3 之后上游新增），
配方不引用、不打包它。R47 `lang-preflight`：task=cpp / detected=c（兼容族）→ 通过。

### 对话 #3（2026-09-10，探索编译 + clang 补丁）
`make` 直接失败：`cc -Wall -c -g …` → `make: cc: No such file or directory`
（Error 127）。根因：OHOS musl 工具链只提供 `clang`，没有 `cc` shim；
而 0.2.3 的 Makefile 硬编码 `CC=cc` / `LD=cc`。
在探索工作树中把 Makefile 的 `CC=cc`→`CC=clang`、`LD=cc`→`LD=clang`
后 `make -j1` 成功，`make install PREFIX=$TEST_PREFIX` 安装
`bin/ondir` + `share/man/man1/ondir.1`。补丁由
`ohc-run.py refresh-patch --auto` 生成（R3，非手写）。

### 对话 #4（2026-09-10，功能验证 + 上游测试清点）
功能验证：`ondir -V` → `This is OnDir version 0.2.3`（exit 0）；
无参数 → `Not enough arguments` + usage，exit 1；
临时 `~/.ondirrc` 中 `enter /ondir_test/child` / `leave /ondir_test/child`
在目录切换时正确回吐命令（含正则捕获 `enter ~/Projects/([^/]+)` → `PROJ_xxx`）。
上游测试清点（R51）：`make -n check` → `No rule to make target 'check'`；
无 tests/ 目录、无测试文件 → 上游 0 测试。

### 对话 #5（2026-09-10，固化配方 + finish）
`conan-init` 生成的 autotools 模板对 ondir 完全不适用（无 configure），
改写为 Makefile/application 配方：patches + `make -j1` + package()
安装 bin/man/hooks/example/docs。test_package 采用可执行包模式
（conanfile.py + test.sh）做真实功能断言。软件级新增 `commands.json`（R38）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make` 报 `cc: No such file or directory`（Error 127） | Makefile 硬编码 `CC=cc`/`LD=cc`；OHOS musl 工具链无 `cc`，只提供 `clang` | `patches/0001-Makefile.patch` 将 `CC`/`LD` 改为 `clang`（refresh-patch --auto 生成） |
| 2 | `init-build` 构建系统误判为 autotools | 探测依据（有 Makefile）不区分手写 Makefile 与 autotools 产物 | 配方按真实情况写成 Makefile/application，manifest 记录 `build_system: makefile` |
| 3 | L2 冒烟探测 `--version`/`--help` 失败 | 上游只实现 `-V`，其余选项按 "Unknown argument" 报错退出 | 不做上游行为修改（R8）；L2 为非阻塞 warn，已在 manifest/notes 记录 |

## 源码修改

- `patches/0001-Makefile.patch`（唯一补丁，portability）：
  - `CC=cc` → `CC=clang`
  - `LD=cc` → `LD=clang`
  - 无平台宏（不含 `__OHOS__`），对非鸿蒙平台也成立（`clang` 是通用的
    POSIX 工具链驱动名）；符合 R8 的"补丁不引入平台宏"口径。

## 依赖版本

无第三方依赖（`requirements()` 为空）。仅使用 musl libc 自带的
`regex.h`、`sys/stat.h`、`unistd.h getcwd()`。

## 验证结果

```bash
# 探索阶段（源码树内）
$ make -j1 && make install PREFIX=$TEST_PREFIX
$ $TEST_PREFIX/bin/ondir -V
This is OnDir version 0.2.3                # exit 0
$ $TEST_PREFIX/bin/ondir
Not enough arguments
usage: ondir [-V] <old-directory> [<new-directory>]
...
                                           # exit 1
# 功能：临时 ~/.ondirrc，enter/leave 段落按目录匹配回吐命令
$ HOME=<tmp>/home ondir /ondir_test /ondir_test/child
echo ENTER_CHILD
$ HOME=<tmp>/home ondir /ondir_test/child /ondir_test
echo LEAVE_CHILD

# 固化阶段（conan，W3 本地 CI）
$ conan create archives/o/ondir/0.2.3 -pr:h=ci/conan/profiles/ohos-aarch64 \
    -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# → test_package 运行 test.sh，18 断言全过（见 .ci-result.json）
```

## 上游测试评估（R51）

ondir 0.2.3 **不提供任何自动化测试套件**，清点证据：

- `make -n check` → `make: *** No rule to make target 'check'.  Stop.`（exit 2）
- `make -n test` → 同上，无 `test` target
- 0.2.3 tarball 共 19 个文件，无 `tests/` 目录、无 `*test*` 文件
- Makefile 目标仅：`ondir`（默认）、`clean`、`install`、`package`、
  `slackware`、`rpm`、`dist`、`dep`

=> 上游测试：0 文件 / 0 用例 / 0 断言（详见 `test_package/MANIFEST.yml`）。
因此本包的消费者侧验证全部由 `test_package/test.sh` 补齐（R34/R51）：
执行已安装的 `ondir` 二进制，断言 `-V` 版本、无参数退出码与 usage 文案、
未知选项拒绝、真实 enter/leave 钩子回吐、以及 man/hooks/example/docs
文件存在，共 18 处断言。

## 交付物

conan 包布局（`conan create` 产物）：

| 路径 | 说明 |
|------|------|
| `bin/ondir` | 命令行主程序 |
| `share/man/man1/ondir.1` | man page |
| `share/ondir/scripts.sh` / `scripts.tcsh` / `scripts.zsh` | shell 集成钩子 |
| `share/ondir/ondirrc.eg` | 示例配置文件 |
| `share/doc/ondir/{README.rst,COPYING,ChangeLog,AUTHORS,INSTALL}` | 文档 |

## 注意事项

- 0.2.3 与 master/HEAD（如 55279f03…）**不是同一份快照**，本包严格使用
  发布提交 cb2f9f8b21e3，勿用 master 快照替换。
- 补丁只做 `cc → clang` 的驱动名替换，不含平台宏；后续若上游新增
  `--version`/`--help`，可另行评估是否同步，但不应在本适配 PR 中改动上游 CLI 语义。
---

**编译结束**: 2026-09-10 10:41
**最终状态**: built
