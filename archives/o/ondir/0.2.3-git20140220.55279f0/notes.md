# ondir 0.2.3-git20140220.55279f0 鸿蒙 PC 适配笔记

## 状态（2026-09-19）

- conan create：**通过**（鸿蒙真机，隔离 `CONAN_HOME=~/work/psj/ch-ondir`，退出码 0）
  - 配方 revision `88b7aa9a2b2b04b2cef08cd8b25b3b33`，包ID `6b129b068851896169fae42d399fa922d239ce8a`，包 revision `d192fe084775cb196890b4349e95b931`
  - 日志关键行：`Sources correctly downloaded from https://codeload.github.com/alecthomas/ondir/tar.gz/55279f0366…`
    → `Apply patch (portability): 0001 Makefile use clang instead of cc` → `RUN: make -j1` → `OnDir is built.`
    → `test_package` 末行 `ALL TESTS PASSED`（6 用例 / 19 断言，含真机执行 `bin/ondir -V` 与 enter/leave hook 回吐）
  - 安装包内 `bin/ondir`：`ELF 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)`，`readelf -d` 只有 `NEEDED libc.so`；真机直接执行输出 `This is OnDir version 0.2.3`
- 上游自动化测试：0（上游不提供自动化测试套件，Makefile 无 check/test 目标，N=0，按赛事口径申报，并以 19 项消费者断言验证产物可用）
- 版本来源：上游提交 `55279f0366c32e4295c9f114cbee5ac7776e4d53`（提交时间 2014-02-20 23:11:42 +1100，
  主题 `Merge pull request #3 from xuhdev/patch-1`）。该仓库没有 git tag，因此提交 sha 是版本号的唯一权威坐标，
  与任务版本 `git20140220.55279f0` 的日期、短 sha 逐位吻合；禁止用分支头顶替（本例恰好等于 master 头，
  但配方仍按完整 sha 取源码，不依赖分支名）。

## 与已合入 0.2.3 的关系

`archives/o/ondir/0.2.3`（任务 #7187，PR #9316）取的是发布提交 `cb2f9f8b21e3`（2013-09-19）。
两个提交之间的全部差异只有 2 个文件：

```
$ git diff --stat cb2f9f8b21e336165fc0a310d677fda75c8e8513 55279f0366c32e4295c9f114cbee5ac7776e4d53
 ondir_prompt_hook.fish | 6 ++++++
 scripts.zsh            | 3 ++-
```

即本版本相对 0.2.3 的实质变化 = 新增 fish shell 钩子（`f1fc581 add ondir prompt hook function for fish shell`）
+ zsh 钩子改用 `chpwd_functions`（`3126dff Use chpwd_functions to avoid modifying chpwd`）。
`Makefile` 在两个提交之间**逐字节相同**，因此 `patches/0001-Makefile.patch` 与 0.2.3 复用同一份、
补丁段（`conandata.yml` 的 `patches:`）不变；`VERSION=0.2.3` 未随提交递增，故 `-V` 仍报 `0.2.3`（上游如此，非适配引入）。
本 PR 的 packaging 因此**多打包一个文件** `ondir_prompt_hook.fish`（→ `share/ondir/`），消费者测试同步断言其存在。

## 编译环境

- 构建系统：makefile（手写 Makefile，无 autoconf/configure）
- 编译器：clang 15（OHOS SDK `ohos-sdk@26.0.0.18`，profile `ohos-aarch64`，`os=OHOS os.version=6.0 arch=armv8`）
- 依赖：无外部依赖（仅 POSIX `regex.h` / `sys/stat.h` / `unistd.h getcwd`）→ 天然满足 R36
- `make` 固定 `-j1`（手写单发 Makefile，无并行安全声明）

## 源码修改

- `patches/0001-Makefile.patch`（唯一补丁，portability）：`CC=cc` → `CC=clang`，`LD=cc` → `LD=clang`。
  OHOS musl 工具链只提供 `clang`，没有 `cc` 垫片，否则 `make` 报
  `make: cc: No such file or directory` (Error 127)。

## 上游测试评估（取证命令）

- `make -n check` → `make: *** No rule to make target 'check'.  Stop.`（退出 2）
- `make -n test`  → `make: *** No rule to make target 'test'.   Stop.`（退出 2）
- 目标全集：`grep -nE '^[A-Za-z0-9_.-]+:' Makefile` → `clean install package slackware rpm dist dep` + `$(TARGET)`，无测试目标
- 归档包共 20 个文件，无 `tests/` 目录、无 `.sh/.py` 测试脚本：
  `tar tzf <tarball> | grep -icE 'test|spec'` → 仅命中 `ondir.spec`（RPM 打包描述文件，非测试）

## 消费者测试（鸿蒙特有，`test_package/test.sh`）

真机实际执行安装包里的 `bin/ondir`，6 个用例 / 19 项断言：

1. `bin/ondir` 存在且可执行（1）
2. `-V` 输出 `This is OnDir version 0.2.3`（1）
3. 无参调用退出码非 0，且打印 `Not enough arguments` 与文档化的 usage 行（3）
4. 未知选项 `--bogus` 被拒绝且退出码非 0（1）
5. 用临时 `~/.ondirrc` 驱动一次真实目录切换：enter 输出严格等于 `echo ENTER_CHILD`、leave 输出含 `echo LEAVE_CHILD`（2）
6. 安装的 man / shell 钩子（含本版新增的 fish 钩子）/ 示例配置 / 文档共 11 个文件存在且非空（11）

第 1 项同时满足 CI 的 L1e 破坏性反向验证（把 `bin/` 移开后脚本必须失败）。
