# shfm 0.4.2 适配笔记

## 编译环境

- 构建系统: custom（单文件 POSIX sh 脚本，没有 configure/make，也没有任何编译步骤；`init-build` 把它误判为 autotools，已按 Conan `application` 手写配方，与已合入的 `unfoo` 同形态）
- 编译日期: 2026-10-04
- 编译器: 不适用（无 C/C++ 源码）；test_package 的消费者程序用 `/data/service/hnp/bin/clang`（Clang 15.0.4，OHOS aarch64，静态链接）
- 状态: built

## 语言预检（R47）

- 只读预判 `detect_language` 输出 `other`（build_system=none，无源文件可统计）。上游只有一个 426 行的 `#!/bin/sh` 脚本 `shfm`，另有 `README`、`LICENSE` 和只跑 `shellcheck shfm` 的 GitHub workflow。
- 这是 Shell 库，大赛接受 Shell 适配，所以按 `--lang other` 如实申报并跑 `lang-preflight`（匹配通过，未伪报 `cpp`，未产生 `env_unsupported` 终态）。

## W0 / W0b

- W0 依赖发布检查：运行时依赖只有 POSIX sh 与 `[`、`printf`、`dd`、`stty`（系统工具），没有任何 Conan 依赖，因此没有需要 `conan download` 的包，`requirements()` 为空。
- W0b 历史核验：仓库里没有 shfm 的历史归档（`archives/s/` 下只有无关的 `shfmt`）。

## 编译步骤

1. `init-build shfm 0.4.2 --url=https://github.com/dylanaraps/shfm/archive/refs/tags/0.4.2.tar.gz`，随后对 `.work` 里每个文件 `cp --remove-destination` 断开与 `.orig` 的硬链接（E543）。
2. 源码核验：tag 归档 sha256 `3861d1130cefbeef4306da686997143c95386c6b5a229472b11053a2da0ddfe4`，三次独立下载（github.com archive 两次、codeload.github.com 一次）一致；tar 头 `comment=8ad3756a1c93d61042c79af49f0dbaac1d37b6c0` 与 `git ls-remote` 的 `refs/tags/0.4.2` 一致；脚本内版本串为 `shfm 0.4.2`。
3. 无构建系统：手工“安装”就是 `install -m 0755 shfm $TEST_PREFIX/root/usr/local/bin/shfm`（staging），配方里等价于 `package()` 复制并 `chmod +x`。`build()` 只应用补丁并做 `sh -n shfm` 语法检查。
4. 实测发现 cd-on-exit 在 mksh/bash/zsh 下失效（见下），修改 `.work/shfm`，`track-edit add` + `refresh-patch --auto` 生成 `patches/0001-shfm.patch`。
5. `conan-verify`（G1/G2/G3 通过，G2 即 `conan create` + test_package）与 `finish`（W2 结构检查、R36 依赖检查、W3 本地 CI）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 判 `BUILD_SYSTEM=autotools`，`conanfile.py`/`test_package` 模板“不可用”，生成的 `manifest.yaml` 全是占位符 | 目录里没有任何构建文件，检测器回落到 autotools | 手写 `application` 配方，`manifest.yaml`/`notes.md` 手工填实；不为它造 configure 步骤 |
| 2 | `cd "$(shfm)"` 在 mksh、bash（含 `--posix`）、zsh 下拿到空串，目录路径被直接打在终端上；dash 下正常 | shfm 以 `main "$@" >/dev/tty` 运行，`exit` 后由 EXIT trap 执行 `printf '%s\n' "$PWD" >&1`。dash 在执行 trap 前撤销函数重定向，其余三种 shell 不撤销，`>&1` 仍是 `/dev/tty`。OHOS 的 `/system/bin/sh` 是 mksh、hnp 提供 bash，都在受影响一侧 | 补丁 `0001-shfm.patch`：顶层 `exec 3>&1` 保存调用者 stdout，trap 改写 `>&3`，`cmd_run` 起的子进程 `3>&-`（见“源码修改”）。知识草稿 E14731-draft-6E2B |
| 3 | 无控制终端时 shfm 根本起不来，连 `--version` 也不行：dash `cannot create /dev/tty: No such device or address`（rc=2），bash `/dev/tty: 没有那个设备或地址`，mksh `/dev/tty: create: No such device or address` | `main "$@" >/dev/tty` 在第 431 行；`--version` 的输出也走 `/dev/tty`，不进 stdout | test_package 用 `pty.openpty()` + `TIOCSCTTY` 给 shfm 一个控制终端、stdout 接管道，`drive_shfm.py` 自己打按键 |
| 4 | 键盘循环 `while key=$(dd ibs=1 count=1 2>/dev/null)` 在 EOF 时 `dd` 仍返回 0 | 上游没有处理 EOF，终端被关掉而没有 SIGHUP 时会空转 | 不改上游；驱动脚本每个步骤带 30 秒超时，失败时对进程组 `SIGKILL`，必须以 `q` 正常退出 |

## 源码修改

`patches/0001-shfm.patch`（由 `refresh-patch --auto` 从 `.orig`/`.work` 差异生成，+7/-2，三处）：

- `term_reset()`：`printf '%s\n' "$PWD" >&1` → `>&3`。
- `cmd_run()`：`"$@" ||:` → `"$@" 3>&- ||:`，子进程不继承 `$(...)` 捕获管道的写端。
- 脚本末尾：`main "$@" >/dev/tty` 之前加 `exec 3>&1`。

补丁是纯 POSIX sh，没有平台宏、没有 `__OHOS__`，在 dash、bash、mksh、zsh 下行为一致，适合向上游提交。`shellcheck shfm`（上游唯一的 CI 检查）对原版与补丁版均为 0 条告警。

## 依赖版本

无 Conan 依赖。运行期工具：POSIX sh、`[`、`printf`、`dd`、`stty`，以及控制终端。本机验证用的 shell：dash 0.5.12、bash 5.2、zsh 5.9、mksh R59 (Debian 12 包，作为 OHOS `/system/bin/sh` 的同源替身，**未在 OHOS 真机上运行**)。

## R51 上游测试清点与执行

- 清点（官方 tag 归档 `shfm-0.4.2/`，共 4 个文件：`LICENSE`、`README`、`shfm`、`.github/workflows/main.yml`）：`tests/` 目录 0 个，ctest/pytest 注册 0 个，Makefile 不存在。上游唯一的自动化检查是 workflow 里的 `shellcheck shfm`（静态检查，不是测试用例）。
- 执行：`shellcheck 0.9.0 shfm` 对原版 rc=0，对补丁版 rc=0，均无告警。上游测试用例数 N=0，通过率不适用；功能验证由 test_package 补齐，见下。

## rule12：鸿蒙特有测试（N=2，完整消费者流程）

文件：`test_package/conanfile.py`、`drive_shfm.py`、`consumer.c`、`CMakeLists.txt`（`MANIFEST.yml` 同步登记）。流程是“被测包参与构建 → 编译消费者程序 → 运行”：

1. 用例 1（`drive_shfm.py`，由 `build()` 通过 `self.run` 执行）：对 Conan 包里的 `bin/shfm`，在 pty 上（shfm 需要 `/dev/tty`、`stty`、`dd`）分别用 `bash shfm` 和直接执行（`#!/bin/sh` shebang）各跑一遍：断言屏幕列出 `alpha/`、`ohos_consumer/`、`zeta.txt`，状态行 `(1/3)`→`(2/3)`，`j`、`l` 进入 `ohos_consumer/`（`(1/2)`），在 `consumer.c` 上按 `l` 触发 `$SHFM_OPENER`（记录参数且 fd 3 必须已关闭），`q` 退出后退出码为 0、**stdout 恰为 `<workdir>/ohos_consumer`**。这是补丁改动的代码路径；原版在 bash 下 stdout 为空，测试会失败。
2. 用例 2（`consumer.c`）：把用例 1 中 shfm 打印的目录作为 CMake 源目录（`-DSHFM_SELECTED_DIR`），用 OHOS profile 的 Clang 15 交叉编译并静态链接为 AArch64 ELF，在该目录里用 `qemu-aarch64` 运行（aarch64 原生 runner 直接运行），程序检查 `getcwd()` 等于 shfm 输出、目录内容恰为 `consumer.c`+`notes.txt`。

执行证据（本地实跑，未 skip）：`conan-verify` 的 G2 日志 `reports/conan-create.log` 含 `RUN: sh -n shfm`、`PASS shfm[bash]`、`PASS shfm[sh-shebang]`、`The C compiler identification is Clang 15.0.4`、`Linking C executable shfm_ohos_consumer`、`RUN: qemu-aarch64 .../shfm_ohos_consumer ...` 与输出 `shfm cd-on-exit dir ...: consumer.c + notes.txt, built and run for OHOS aarch64`，退出码 0。

负向对照（同一份 `drive_shfm.py`，`run_scenario` 在 6 种 shell 调用下）：

| 脚本 | dash | bash | bash --posix | mksh | mksh -o posix | zsh |
|---|---|---|---|---|---|---|
| 原版 shfm 0.4.2 | PASS | FAIL（stdout 为空） | FAIL | FAIL | FAIL | FAIL |
| 补丁版（staging 安装） | PASS | PASS | PASS | PASS | PASS | PASS |

去掉补丁第二处（`3>&-`）的对照脚本在 bash 下被检出 `fd3=open`。

限制（如实说明）：消费者是静态链接的 aarch64 程序，目的是在 x86 runner 上经 QEMU 做功能验证；shfm 本身是 shell 脚本，不是 ELF，没有声称它在 OHOS 真机上运行过；mksh 用的是 Debian 的 R59，不是 OHOS 自带构建。

## 门禁说明与知识

- 软件级 `commands.json` 按 PF8/R38 放在 `archives/s/shfm/`（CLI 包必须有），与 PF9 对“新增软件首个版本”的路径规则存在结构性冲突，PR 正文登记，不在配方里绕过。
- 新知识草稿 `E14731-draft-6E2B`：被重定向函数内 `exit`，EXIT trap 的 stdout 语义因 shell 而异（只有 dash 先撤销重定向）。`engine` 对 `/dev/tty` 与 `stty` 两条报错无命中，`draft-review` 判 `create`（最近条目 E239，分数 0.09），pty/TUI 类既有草稿讲的是如何驱动 TUI，没有覆盖此语义。

## 验证结果

```bash
shellcheck shfm                                  # 原版 rc=0，补丁版 rc=0
conan-verify shfm 0.4.2                          # G1 PASS / G2 PASS（conan create + test_package）/ G3 PASS
finish shfm 0.4.2 built                          # W2 结构检查 PASS，R36 无依赖，W3 本地 CI PASS（见下）
```

W3 本地 CI（`reports/w3-local-ci.log`，由 `finish` 生成 `.ci-result.json`）：`setup.sh`、`build_and_test.sh` 均通过；L0 质量门禁、KC、JC1–JC6 全过；`conan create` 通过，L1a/L1b 有 test_package 执行证据（含 `PASS shfm[bash]`、`PASS shfm[sh-shebang]` 与 qemu 运行消费者）；L1e 破坏性反向验证把 `bin/` 移走后测试确实失败（`test genuinely depends on shfm`）；L2 `shfm --version/--help` 因没有控制终端报非阻塞告警（上游行为，见注意事项）。

`finish` 的非阻断框架项（与本包无关，不为规避它们改动框架文件）：G0 clean-verify 无条件执行 `./configure`，脚本包没有该文件（`exit 127`）；`gen_summary` 报 `'str' object has no attribute 'append'`；`finalize-archive` 与 submit 就绪预检仍检查已废弃的 `packaging/` 与 tar.gz。`finish` 另外改写了 `conandata.yml`（镜像列表）与 `manifest.yaml`，已在提交前还原为人工版本。

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/s/shfm/{README.md,manifest.yaml,commands.json}` | 软件级元数据，CLI 声明 |
| `archives/s/shfm/0.4.2/{conanfile.py,conandata.yml,patches/0001-shfm.patch}` | 配方、源码声明与补丁 |
| `archives/s/shfm/0.4.2/test_package/` | pty 驱动 + OHOS aarch64 消费者 |
| `knowledge/drafts/E14731-draft-6E2B.{kv,md}` | 知识草稿，等待主编审核 |

## 注意事项

- shfm 需要控制终端：没有 `/dev/tty` 时任何调用（含 `--help`/`--version`）都会失败，这是上游行为，补丁不改。
- `shfm --version/--help` 的输出走 `/dev/tty`，不进 stdout；只有退出时的目录路径经 fd 3 进入调用者的 stdout。
---

**编译结束**: 2026-10-04 01:28
**最终状态**: built
