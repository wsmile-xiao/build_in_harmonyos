# utalk 1.0.2 适配笔记

## 编译环境
- 构建系统: makefile（手写 POSIX Makefile，无 autotools/cmake/meson）
- 编译日期: 2026-09-30
- 编译器: clang（/data/service/hnp/bin/clang，OHOS SDK llvm）
- 目标: ohos-aarch64（armv8）
- 状态: built（真机真实构建 + conan create 通过；未上传发布）

### 对话 #
- 目标库 utalk/1.0.2，唯一强制第三方依赖 ncurses/6.6（W0 conan download EXIT=0，可消费）。
- 上游无自动化测试（stest.c 未随包发布），上游测试入口实测不可运行，详见 reports/build-report.md。
- 全程只处理 utalk 自身文件；未混入依赖库源码/recipe。

## 编译步骤

```bash
# 1. 构建（源码树内，命令行为 make 变量覆盖 Makefile 赋值）
make -j1 \
  CC=/data/service/hnp/bin/clang \
  LIBS="-L<ncurses>/lib -lncursesw" \
  LDFLAGS="-Wl,--allow-multiple-definition" \
  utalk
# 产物: utalk (ELF 64-bit LSB arm64, musl, PIE)

# 2. 安装（package() 内为分阶段拷贝，不使用上游 make install）
#    utalk        -> bin/
#    utalk.1      -> share/man/man1/
#    LICENSE      -> licenses/
#    ncurses terminfo -> share/terminfo/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `menu.c:677: error: use of undeclared identifier 'LIBDIR'` | 命令行覆盖 `CFLAGS` 丢弃了 Makefile 的 `OPTS`（含 `OPT5=-DLIBDIR="..."`），`menu.c` 的 `HELPFILE` 宏依赖它 | 不覆盖 `CFLAGS`，仅通过命令行传 `CC`/`LIBS`/`LDFLAGS`，让 Makefile 自带 `OPTS` 生效 |
| 2 | `ld.lld: error: duplicate symbol: beep`（链接） | 静态 `libncursesw.a` 提供 `beep`，与 utalk `termcap.c:140 beep()` 重名；静态链接下不能靠动态符号覆盖 | `LDFLAGS` 加 `-Wl,--allow-multiple-definition`，目标文件定义优先（仓库先例 cflow/dovecot/ettercap） |
| 3 | 无 tty 运行报 `I can only run on a tty, sorry` | utalk 需要控制终端（termio/termcap 初始化） | 非缺陷：作为确定性行为用于测试断言 T4；pty 用例 T6 验证全屏可用 |

## 源码修改

无补丁（`patches_applied: []`）。上述问题均通过 Conan 配方侧的编译/链接参数解决，未改动上游源码。

## 依赖版本

- `ncurses/6.6`（宽字符，静态链接；OHOS 制品仓可消费）

## 验证结果

```bash
# 上游测试入口（实测不可运行）
$ make test
make: *** No rule to make target 'stest.o', needed by 'test'.  Stop.
EXIT_CODE=2

# 消费者测试（test_package，真机执行）
$ bash test_package/test.sh <pkg>/bin/utalk
UTALK_TEST_RESULT pass=8 fail=0 skip=0
utalk tool consumer tests PASSED

# pty 全屏渲染（ncurses + terminfo 生效）
$-s 0 (TERM=xterm-256color, pty)
[m][o][*]------------------- utalk version 1.0.2 ------------------------------
[n]---------------------- waiting for connection... ---------------------------
```

## 注意事项

- 上游 `make test` 引用未随源码包发布的 `stest.c`，因此**上游无自动化测试**（详细清点见 `test_package/MANIFEST.yml` 与 `reports/build-report.md`）。
- 编译期内置的 `LIBDIR` 沿用上游默认（`/usr/local/lib`），`utalk.help` 帮助文件上游自身也未安装；不影响主功能。
- 二进制为 PIE（ELF shared object / musl），运行时仅依赖 `libc.so`。
- ncurses 为系统同名库，按 R26 静态链接；因此 `beep` 符号与 ncurses 重名，需 `-Wl,--allow-multiple-definition`（目标文件定义优先）。

## 本机（OHOS 设备）运行说明

- 在本机以 `conan create …` 直接构建时，若 conan 进程由 agent 工具链（python→sh 多级链）启动，工具链驱动可能**静默失败**（无任何编译器输出、exit 1，而 `clang --version` 正常）。已在 `build()`/`test()` 中通过把 `make`/`test.sh` 的输出以管道捕获（`io.StringIO()`，conan 转 subprocess.PIPE）规避；在独立 bash 会话（`nohup bash … &`）中直接运行同样正常。
- 本地 CI 模拟的 junk 检查（`JC`）在 full 模式下会被仓库历史遗留的 `archives/c/cloog/.../.build-closed` 等状态文件误伤，可用 `JUNK_PR_DIFF=<仅本包文件清单的 diff>` 走 prdiff 模式。
- `clean-verify`（G0）对纯 Makefile 项目会固定执行 `./configure`（exit 127 → 记为失败），属框架对该类项目的已知非阻塞项；完整构建由 conan-verify(G2)/W3 覆盖。
- `finish` 退出码为 1 的两个非阻塞步骤均**与本包无关**，已定位取证：
  - `step5b`（W5 知识图谱完整性）：仓库全局 2438 条历史草稿与 E219/E253/E305 字段缺失告警；本包 `知识完整性检查通过`（`knowledge_count=2 unreferenced=0`）。
  - `step8`（gen_summary）：`'str' object has no attribute 'append'`。全仓 9016 个版本级 manifest 扫描，仅 `archives/q/qpdf/12.3.2/manifest.yaml`、`archives/q/qpdf/12.3.2.1/manifest.yaml` 触发该解析器缺陷；本包 3 个 manifest 均解析通过。
---

**编译结束**: 2026-09-30 08:36
**最终状态**: built
