# mmh 0.4 — HarmonyOS PC 适配

mmh（meillo's mail handler）是经典 MH 邮件系统的现代化重写：消息以「一条
消息一个文件」的模块化方式存储（文件夹即目录），提供完整的 MIME 支持
（`mhbuild` 构建、`mhlist`/`mhshow` 浏览、`mhstore` 提取附件）、gpg 集成
（`mhsign`/`mhpgp`）、模板/别名/分发列表、`pick` 条件检索等。绝大多数命令
面向脚本非交互使用，也可以配合 `ap`/`mmh` 等进入 curses 交互界面。

本归档是上游 0.4 在 HarmonyOS PC（aarch64-linux-ohos）上的适配。Conan 包
类型为 application：安装 `bin/` 的 40 个命令（34 个 C 程序 + 6 个脚本）
与 8 个命令链接、`lib/` 的辅助二进制，因此软件级目录提供 `commands.json`。

上游地址：https://marmaro.de/prog/mmh/

## 适配要点

- **config.guess / config.sub**：2005 年版探测脚本补 HarmonyOS 分支与
  `linux-ohos` 内核项，configure 可正确得到三元组
  `aarch64-unknown-linux-ohos`（不借助 `--build/--host`）。
- **autotools 临时目录**：HMDFS 把目录 owner 映射为固定 UID，`umask 077`
  创建的 `confXXXXXX` 临时目录不可写，改为 `umask 022`（E011）。
- **ncurses**：OHOS ncurses/6.6 只提供宽字符库 `libncursesw.a`（无
  `libncurses.a`），`tgetent` 的探测顺序在 `ncurses` 后补 `ncursesw`。
- **临时目录**：OHOS `/tmp` 只读（真机探针实测不可写），`test/setup-test`
  与脚本命令 `mhsign`/`mhpgp`/`sendfiles` 的硬编码 `/tmp` 改用
  `${TMPDIR:-/tmp}`（否则 `mkdir /tmp/<name>.$$` 在脚本入口即失败）。
- **锁机制**：mmh 默认 dot-lock 用 `link(2)` 原子创建 `.lock` 文件，
  HMDFS 拒绝硬链接（EPERM）；配方以 `--with-locking=fcntl` 改用
  fcntl 内核锁。
- **消息入箱回退**：`folder_addmsg()`（`refile`/`rcvstore`/`mhstore -file`
  入箱的公共路径）的复制回退原本只覆盖跨设备错误（EXDEV），补丁扩展到
  EPERM/EOPNOTSUPP，HMDFS 上照常可移动/投递消息。
- **命令别名链接**：`install-lcmds` 用 8 个硬链接造命令别名
  （`flists`/`folders`/`fnext`/`fprev`/`unseen`/`prev`/`next`/`scan`），
  HMDFS 拒绝硬链接；安装改以 `LN=cp` 复制（命令本体按 `argv[0]` 分派，
  语义等价）。
- **预生成产物冻结**：发行包自带的 `configure`/`config.h.in`/`stamp-h.in`/
  `sbr/dtimep.c` 是 2019 年 autoconf/flex 的产物，与宿主工具不同代；配方
  在补丁应用后统一冻结其时间戳，避免 make 触发重新生成。
- **构建期脚本调用**：`man/`/`sbr/`/`uip/` 的 Makefile 以反引号直执行
  `version.sh` 拼装版本串，`man/` 目录另直执行 `gettitles.sh`/`mh-chart-gen.sh`
  生成标题与命令图；OHOS 内核拒 shebang 脚本 execve（make 报 Permission
  denied rc 126），补丁统一改 `sh` 前缀驱动（否则 VERSION 静默变空、
  `make all` 中断于 `titles`/`mh-chart.man7`）。
- **公共符号合并**：2019 年版 C 代码依赖 GCC<10 的暂定定义合并语义
  （`char *tmp;` 在 mhbuild.c/mhparse.c 各定义一次、另四处 extern 共享），
  clang≥11 默认 `-fno-common` 会产生链接期 duplicate symbol；配方在
  CFLAGS 追加 `-fcommon` 复现上游构建语义。
- **脚本型命令**：7 个文件以上游 shell 脚本形式安装（`bin/` 的 `mmh`/
  `mhsign`/`mhpgp`/`print-mimetype`/`sendfiles`/`whatnow2` 与 `lib/` 的
  `mmhwrap`）；OHOS 内核拒绝 shebang 脚本 execve（rc 126 EACCES），真机
  调用需加 `sh` 前缀（C 命令不受影响）。
- **format/组件文件定位**：`etcpath()` 原本只查 `$MMH`（用户目录）与编译期
  `NMHETCDIR`（conan 以 `--prefix=/` + DESTDIR 打包，编译期值固定为 `/etc`，
  设备上不存在），`scan.default`/`pick.default`/`mhn.defaults`/`components`
  等随包文件位于包内 `etc/`；补丁让 `etcpath()` 先查 `MMHETC` 环境变量，
  配方经 `runenv_info` 导出 `MMHETC=<包>/etc`（VirtualRunEnv 对消费者自动
  生效，`inc`/`scan`/`pick`/`comp`/`forw` 等即可正常工作）。

## 依赖

- `ncurses/6.6`（静态链接，R26）

## 构建与验证

- `conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64>`
- 上游测试套件入口：`cd test && ./runalltests`（57 个 `test-*` 脚本 /
  28 个目录），真机实测见 `0.4/notes.md`。
- 消费者冒烟 + 端到端用例见 `0.4/test_package/`（12 例）。
