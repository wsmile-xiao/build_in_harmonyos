# GPGME 上游测试的真实前置：AF_UNIX 可用挂载与可重定位 gnupg 的引擎路径

> 本草稿配对 gpgme/1.24.2，依据任务 13785/14628 的 HarmonyOS PC 真机验证记录。

## 触发场景

GPGME 的 Automake 测试套件全部报 `GPGME: Invalid crypto engine`，或 `tests/gpg/Makefile.am`
的 `pubring-stamp` 以 `Error 2` 中断，逐条伴随 `gpg: can't connect to the gpg-agent: IPC
connect call failed`。软件库本身编译、链接、打包都正常，只有测试跑不起来。

## 原因机制

两条独立的平台机制叠在一起：

1. GPGME 不用编译期常量定位引擎，而是执行 `gpgconf --list-components` / `--list-dirs`，
   取字段里的安装前缀拼出 `gpg`、`gpgsm` 路径。随包 `gnupg/2.5.22` 为可重定位以
   `--prefix=/` 发布，于是列表给出 `//bin/gpg`，即设备只读的 `/bin/gpg`（`/bin` 是指向
   `/system/bin` 的符号链接，不可写）。路径不存在时 GPGME 直接得到 `Invalid crypto engine`，
   同一前缀也使 `gpg` 无法自启动 `/bin/gpg-agent`。
2. 上游 `tests/*/Makefile.am` 定义 `GNUPGHOME=$(abs_builddir)`，`gpg-agent` 在该目录里
   bind `S.gpg-agent`。HarmonyOS PC 的用户存储挂载（HMDFS，`/storage/...`，Conan 缓存默认
   落点）拒绝 AF_UNIX：真机原始报错 `gpg-agent[…]: error binding socket
   '/storage/…/S.gpg-agent': Operation not permitted`，Python `socket.AF_UNIX.bind()` 亦返回
   EPERM；同一进程在 `/data/storage/el2/base/cache` 下 bind 与收发均成功。构建根落在前者，
   所有套件在第一条 gpg 调用前就失败。

另外 `make install` 会递归到每个含 `pubring-stamp` 的目录并先构建 BUILT_SOURCES，所以只给
“要跑的套件”准备 agent 不够，安装阶段同样会失败。

## 操作步骤

1. 配方在 `build()` 里探测源码目录能否 `AF_UNIX.bind()`。HMDFS（`/storage`，CI 与
   Conan 默认缓存）返回 EPERM 时，把已打补丁的源码树复制到第一个允许 bind 的目录
   （本机为 `/data/storage/el2/base/cache/gpgme-1.24.2-src`），configure/make/check/install
   都在该副本上进行。各套件仍使用上游的 `GNUPGHOME=$(abs_builddir)`，不改测试文件。
   CI 不会搬走 `CONAN_HOME`，所以这一步必须在配方内完成。该副本的父目录在 CI worker
   上可进入但不可读，直接把 shell 的 cwd 设进去会让 getcwd 失败，libtool 把
   `libgpgmepp.la` 的 relink 记成 `(cd ; $SHELL /libtool ...)`。命令从 Conan
   构建目录 `cd` 到副本并 `export PWD`，libtool 的 `pwd` 在 getcwd 失败时回退到
   `$PWD`，安装前再修正已经写坏的 relink_command。顶层 `make install` 会进入未执行的
   `tests/json` 并重建 `pubring-stamp`（先 `gpgconf --kill all` 再导入，打包的 gpg
   不能自启动 agent）。这些钥匙环不是安装产物，`package()` 只在 `src` 和 `lang`
   执行 `make install`。check 与 install 结束后按 `/proc` SIGKILL 本树的 `gpg-agent` 和 `dirmngr`。
2. 在构建目录内生成 `gpgconf` 包装脚本，仅改写目录列表中的 `//` 前缀为实际包目录，其余调用
   原样 `exec`；执行 `make check` 时把该目录置于 PATH 首位。包装必须是纯输出转发：任何缓冲
   中间层都会让 GPGME 的 gpgconf 会话卡死。
3. 遍历已配置的 Makefile，对每个含 `pubring-stamp` 的目录预建 0700 权限的 GNUPGHOME，写入与
   上游 `start-stop-agent` 等价的 `gpg-agent.conf`（`pinentry-program`、`disable-scdaemon`、
   `allow-loopback-pinentry`），再 `gpg-agent --homedir <dir> --daemon` 起 agent，之后才进入
   `make check` 与 `make install`。
4. 统计上游用例数时按 `TESTS`/`c_tests`/`tests_unix` 计算，`initial.test`/`final.test` 是
   automake 前后置脚本，不计入用例数。
5. 无法完成的套件要单独说明并给出采样证据，不得折算成通过。gpgme 1.24.2 的 `tests/json`
   经 GPGME 的 SPAWN 协议驱动 `gpgme-json -s`，本机子进程 fork 后不替换映像并持续占用 CPU，
   父进程在 gpgme 事件循环等待输出管道 EOF，因此该套件不纳入 `make check`。

## 验证依据

- 上游：https://www.gnupg.org/ftp/gcrypt/gpgme/gpgme-1.24.2.tar.bz2
- 配方：archives/g/gpgme/1.24.2/conanfile.py
- 消费者测试：archives/g/gpgme/1.24.2/test_package
- 上游测试用例统计：37；真机执行并通过：36（`tests/` 3/3、`tests/gpg` 26/26、
  `tests/gpgsm` 7/7）；未执行：1（`t-json`，原因见操作步骤第 5 条）。

## 适用边界

适用于 GPGME 及任何用 `gpgconf` 目录列表解析引擎、并把 GnuPG 家目录设为构建目录的上游包
（如 libgpg-error/libassuan 的集成测试）。HarmonyOS PC 挂载策略或 gnupg 打包前缀变化后需重新
核对；未执行的测试不得报告为通过，也不得把同级软件包配方合并到一个分支。
