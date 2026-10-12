# midish 1.4.0 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

## 适配概况

- MIDI 音序器/过滤器（<https://midish.org/>），实现为小型命令解释器；许可证 ISC
  （manual.html 版权段）。
- 源码：上游作者官方仓库 tag 归档
  <https://github.com/ratchov/midish/archive/refs/tags/v1.4.0.tar.gz>
  （sha256 `44d40459083111c40cf87741e8486d3bc7ebea9b770ca0732c8e775c1b4b1f77`）。
  原发布站点 tarball <https://midish.org/midish-1.4.0.tar.gz>（sha256
  `8eb281a5…5844`）在 CI worker 上极慢且会被中途断流（conan 报 `IncompleteRead` /
  `ConanConnectionError: Download failed`），故改用作者 GitHub 官方仓库；两者内容除
  发布时才生成的 `version.h` 外完全一致，该文件由
  `patches/0002-version-h.patch` 还原。
- 构建系统：**自带 configure 脚本 + Makefile.in**（非 autotools），就地构建；
  `configure` 支持 `--prefix/--bindir/--datadir/--mandir/--enable-alsa/--enable-sndio`
  与 `CC=/CFLAGS=/LDFLAGS=` 直通。
- 产物（`make install` 实测）：`bin/midish`（ELF64 可执行）、`bin/smfplay`、
  `bin/smfrec`（/bin/sh 脚本）、`share/man/man1/{midish,smfplay,smfrec}.1`、
  `share/doc/midish/{README,manual.html}`、`share/examples/midish/{midishrc,sample.msh}`。

## 上游测试入口核验（R51）

- `Makefile.in` 存在 `check` 目标：`@cd regress && ./run-test *.cmd`。
- `regress/` 内 143 个 `.cmd` + 对应 `.res` 期望结果，`run-test` 输出 TAP 风格
  `1..143` / `ok <name>` / `not ok <name>`，并对实际输出与期望做 `diff -u`。
- `run-test` 通过管道把脚本喂给 `../midish -b`，要求解释器在 stdin EOF 时退出。
- 因此上游**有**自动化测试入口（143 例），配方在 `build()` 中真实执行 `make check`。

## 平台适配要点（1 个补丁）

**补丁 0001（`mdep-stdin-eof-pollhup.patch`）—— 本适配的核心问题**

- 现象：`printf 'version\n' | midish -b` 永不退出；`make check` 在第一个用例
  `blank_a0` 就挂住（15 分钟 0 例完成）。
- 定位过程：主循环 `while (!done && mux_mdep_wait(1))`；非 tty 路径为
  `if (tty_pfds->revents & POLLIN) { read(...); if (res == 0) { cons_eof = 1; user_onchar(NULL, -1); } }`。
  用最小复现程序实测本平台语义：管道 EOF 时 `poll()` 返回 `revents=0x10`（**只有
  POLLHUP**），有数据时为 `0x11`（POLLIN|POLLHUP）。因此 `revents & POLLIN` 恒为假
  → 解释器永远看不到 EOF → 每轮 poll 立即返回 → 空转不退（进而 143 例全挂）。
- 修复：非 tty 分支改为 `if (tty_pfds->revents & (POLLIN | POLLHUP))` 再 `read()`；
  EOF 时 `read()` 返回 0，走既有 `cons_eof = 1; user_onchar(NULL, -1)` 路径正常退出。
  对原有平台无行为回归（POLLIN 场景不变），补丁为纯可移植性改动、**不含平台宏**（R8 合规）。
- 验证：`printf 'version\n' | midish -b` → rc=0；`make check` → 143/143 通过。

其余平台事实（无需补丁）：

- `uname` = `HarmonyOS` → configure 的 OS 分支不匹配 Linux/OpenBSD，`alsa=no`、
  `sndio=no`、`rt_ldadd` 为空 → 自动选择 `-DUSE_RAW` 后端（mdep_alsa.c/mdep_sndio.c
  在未定义宏时不产出代码），无需任何 configure 参数。
- 零外部依赖：源码只包含 libc/POSIX 头（alsa/asoundlib.h 与 sndio.h 仅在对应后端 TU 内）。
- 打包布局：`--prefix=/ --datadir=/share --mandir=/share/man` +
  `make install DESTDIR=<package_folder>` → 得到 `bin/`、`share/…` 的标准 conan 布局。
- `/tmp` 与 `$TMPDIR` 在本平台只读：midish 的 `save/export` 必须在可写目录执行
  （上游回归套件与 test_package 都写在构建树内）。

## 实测结果（本机，2026-10-10）

- `make check`（在 conan 构建内、真实执行）：**143/143 通过，0 失败，0 跳过**，
  TAP 输出 `1..143`，末行 `Tests passed`，退出码 0。日志：`reports/conan-create.log`。
- 手工构建验证：configure（alsa=no/sndio=no）→ `make -j8` 0 错误 → `make check` 全过
  → `make install DESTDIR=<包>` 后 `bin/midish` 可运行。
- test_package：
  - 消费者工作流（安装后 `bin/midish -b`）：版本输出 `midish 1.4.0`；载入包内
    `share/examples/midish/sample.msh`（54KB 歌曲）→ 另存 `song.msh` → 导出
    `song.mid`（8.2KB，头部 `MThd` ✔ 标准 MIDI 文件）→ 重新载入 `song.msh` 成功。
  - **鸿蒙专项测试**（`test_package/ohos_test.cpp`）：fork+exec 安装后的 `midish -b`，
    向 stdin 管道写入 `version` 后关闭写端，断言进程在 15s 内以退出码 0 结束
    （即补丁 0001 的平台适配点）；断言 `bin/midish` 为合法 ELF64 且 DT_NEEDED 无含
    `/` 路径（可重定位）；`bin/smfplay`/`bin/smfrec` 为可执行 `/bin/sh` 脚本；
    `share/examples/midish/{sample.msh,midishrc}`、`share/doc/midish/{README,manual.html}`、
    `share/man/man1/{midish,smfplay,smfrec}.1` 安装就位。

## 已知限制

1. OHOS 无 ALSA/sndio，MIDI 后端为可移植 raw 后端（`/dev/rmidi*` 之类设备在本平台
   不存在）：midish 的设备相关功能需要有对应设备节点；命令解释器、编辑与
   MIDI 文件导入导出（本适配的验证范围）不依赖设备。
2. `bin/smfplay`、`bin/smfrec` 是面向真实 MIDI 设备的 shell 前端，本平台只验证其
   安装与 shebang，不执行（无设备）。
3. 本机构建环境文件系统不支持 FIFO，make 的 jobserver 不可用，`-j` 会退化为串行
   （本项目 35 个源文件，实际影响可忽略）；CI 使用自身环境，配方与并行度无关。
