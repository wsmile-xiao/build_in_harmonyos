# daemontools-encore 1.11 适配笔记

## 编译环境

- 构建系统: DJB 风格 makefile（无 configure，配置接口是 conf-cc / conf-ld / conf-bin / conf-man）
- 编译日期: 2026-09-11
- 编译器: clang（`/data/service/hnp/bin/clang`，来自 OHOS profile 的 `tools.build:compiler_executables`）
- 状态: built
- 设备: HarmonyOS PC / HongMeng Kernel 1.12.0 aarch64（HMDFS，大小写不敏感）

## 编译步骤

上游 README 规定的流程是「调整 conf-* → `make` → 在 conf-bin/conf-man 首行写安装目录 → `make install`」，配方完全按该接口执行（命令以版本级 `manifest.yaml` 的 `tests.*.command` 与 conan 构建日志为准）：

1. `build()` 生成 `conf-cc`、`conf-ld`，内容取自 Conan 工具链：
   - `conf-cc`：`/data/service/hnp/bin/clang -O3 -DNDEBUG -Wall -Wshadow -Wcast-align -Wwrite-strings`
   - `conf-ld`：`/data/service/hnp/bin/clang`（不加 `-s`：上游原来写 `gcc -s`，本配方不做 strip）
2. `make -j1 -B programs man` 生成 20 个程序与手册页；
3. `package()` 生成 `conf-bin` / `conf-man` 指向包内 `bin/`、`share/man/`，先按 MAN 清单预建安装目录，再 `make -j1 install`，由上游 `./installer` 安装 `BIN` / `MAN` 清单中的文件；
4. `package()` 额外安装 `LICENSE`。

产物：`bin/` 20 个可执行文件（`envdir envini envuidgid fghack multilog pgrphack readproctitle setlock setuidgid setuser softlimit supervise svc svok svscan svscanboot svstat svup tai64n tai64nlocal`）、`share/man/man8/` 19 个手册页、`licenses/LICENSE`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `make clean` 之后 `make install` 报 `make: *** No rule to make target 'MAN', needed by 'install'. Stop.` | TARGETS 清单含 `man` 与 `targets` 两项；HMDFS 大小写不敏感（实测 `os.path.samefile('MAN','man')` 为 True，`rm -f man` 会删除 `MAN`），于是 clean 删掉了发行版自带的 MAN 安装清单和 TARGETS 自身 | 用 `make -j1 -B programs man` 全量重建，不再调用 `make clean`；原始复现（含上句原文）见 `reports/make-clean-scenario.log.md` |
| 2 | `make install` 报 `installer: fatal: unable to write .../share/man/man8/envdir.8: access denied` | `installer.c` 用 `mkdir(target,0700)` 建 `man8` 后 `chmod(target,0755)`；HMDFS 保留创建模式且 chmod 不再生效，目录停在 `drwx--S--- 2700`、属主映射为共享属主（20001006）而进程 euid 为 20020084，随后同进程 `open(O_CREAT)` 即 EACCES（`mkdir -m 700 d && touch d/x` 同样 Permission denied） | 配方按 MAN 清单中的 `d` 行预建目录（组可写），`installer` 的 `mkdir` 落到它已实现的 `errno == error_exist` 分支 |
| 3 | 预建目录后 `make install` 报 `installer: fatal: unable to read setuser.8: file does not exist` | 上游 1.11 的 MAN 清单要求安装 `setuser.8`，但发行版既未提供该文件、Makefile 的 `man` 目标也只生成 `setuidgid.8`（ChangeLog 显示 git 历史里做过 `setuidgid.8 => setuser.8` 改名，发布包未同步）；任何平台未修补时 `make install` 都必然失败 | 补丁 `patches/0001-MAN-optional-setuser.patch`，用 `installer` 自带的 `?` 可选前缀标记该行 |
| 4 | 上游 `make rts` 在设备上永不返回（1200s 超时，`rts` 输出为空） | 21 个用例里 9 个需要 `supervise` 的控制 FIFO，而 HarmonyOS 拒绝用户进程创建 FIFO（`mkfifo(2)` / `mknod(2) S_IFIFO` 均 EPERM，AF_UNIX bind 亦被拒）；`supervise` 以 111 退出后，套件自己的 `waitok` 辅助函数陷入无限等待 | 不用 `make rts` 聚合入口，按用例运行同一份 `00-preamble.sh + rts.tests/<case>.sh` 并与 `<case>.exp` 比对，逐用例加超时；9 个 supervise/svscan 用例记为 NOT_RUN 并在报告中给出原始错误 |

## 源码修改

`patches/0001-MAN-optional-setuser.patch`：把 MAN 清单第 11 行 `c:::644:/man8/:setuser.8:` 改为 `?c:::644:/man8/:setuser.8:`，使用 `installer.c` 已实现的「可选条目」语义（源文件不存在时静默跳过，而不是 111 退出）。除该行外未改动任何上游文件；`conf-*` 是上游 README 规定的配置接口，不是补丁。

## 依赖版本

无 Conan 依赖；链接仅 libc。构建期使用 profile 提供的 `clang 15.0.4`、`ar`/`ranlib`（LLVM）、`GNU Make 4.4.1`。

## 验证结果

上游回归套件（21 个用例）与包内消费者用例（31 项断言）的取数命令写在版本级 `manifest.yaml` 的 `tests.*`；逐用例原始日志见 `reports/upstream-test.log.md`，汇总与根因见 `reports/upstream-tests.md`，安装缺陷三段场景（未修补 / 预建目录 / 打补丁）见 `reports/upstream-install-scenarios.log.md`，`make clean` 误删清单的原始复现见 `reports/make-clean-scenario.log.md`，conan-verify 与 W3 报告见 `reports/conan-verify-report.md`、`reports/w3-local-ci.log.md`、`reports/conan-create.log.md`，L2/L4/L5 补测与两轮清缓存可复现性见 `reports/conan-verify-supplement.md`。

- 上游用例：执行 21 个，通过 12 个；9 个 supervise/svscan 用例因设备 FIFO 策略 NOT_RUN（原始错误 `supervise: fatal: unable to read supervise/control: file does not exist`）。
- 包内消费者用例：31 项断言全部通过，覆盖 20 个程序的交付与真实行为（envdir/envini 变量注入、setlock 争用、softlimit 子进程上限、tai64n↔tai64nlocal 往返、multilog 目录/状态文件、svstat/svc/svok/supervise 的退出码语义），并对 FIFO 能力做运行期探测：可用时跑完整的 supervise/svok/svstat/svc 周期，不可用时断言上游文档化的控制通道错误。

## 注意事项

- `make clean` 在本平台不可用（见问题 1），后续修改配方时不要改回 clean + build。
- 上游 `installer` 会 `chown`/`chmod` 安装目标；HMDFS 下这些操作不改变实际可访问性，配方依赖的是预建目录 + 清单驱动的复制。
- 9 个 supervise 用例的缺口是环境能力限制而非配方问题：`supervise` 在设备上能正确报出控制通道缺失并快速退出（不是挂死），`svstat`/`svc`/`svok` 对未监管目录与不存在目录的退出码与上游文档一致，包内用例已覆盖这部分语义。
