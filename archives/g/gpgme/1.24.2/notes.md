# gpgme 1.24.2

此自建软件包提供 libkleo 与 mimetreeparser 所需的上游 C、Gpgmepp C++ 和 Qt6 绑定。它与已发布但禁用语言绑定的 gpgme/1.24.0 软件包不同。HarmonyOS CI 的 Bash 路径通过当前 PATH 动态查找。

构建期通过 `tool_requires("gnupg/2.5.22")` 提供上游测试引擎 `gpg`/`gpgsm`；GnuPG 仅作为构建与测试工具，不会成为 GPGME 的运行时依赖。

真机接线（HarmonyOS PC / AArch64 / OHOS 6.0 profile / Clang 15）：

- 按 automake 子目录分别调用 `make -C tests check SUBDIRS=`、`make -C tests/gpg check`、`make -C tests/gpgsm check`，各套件沿用上游默认的 `GNUPGHOME=$(abs_builddir)`，未改动任何测试文件。
- 设备用户存储挂载 HMDFS 拒绝 bind AF_UNIX（`gpg-agent: error binding socket '…/S.gpg-agent': Operation not permitted`，同路径 Python `AF_UNIX.bind()` 返回 EPERM，`/data/storage/el2/base/cache` 正常）。CI 的 Conan 缓存在 `/storage`，不会改 `CONAN_HOME`。配方在 `build()` 探测源码目录，bind 失败时把已打补丁的源码树复制到第一个允许 bind 的目录（本机 `/data/storage/el2/base/cache/gpgme-1.24.2-src`），configure/make/check/install 都在该副本上执行，套件仍用上游 `GNUPGHOME=$(abs_builddir)`。
- 可重定位发布的 gnupg 以 `--prefix=/` 打包，`gpg` 自启动去找设备只读的 `/bin/gpg-agent`（`/bin -> /system/bin`），导致 `gpg: can't connect to the gpg-agent: IPC connect call failed` 并使 `pubring-stamp` 以 `Error 2` 中断。配方对每个含 `pubring-stamp` 的目录预建 0700 GNUPGHOME、写入与上游 `start-stop-agent` 等价的 `gpg-agent.conf`（含 `allow-loopback-pinentry`），再预启动 `gpg-agent`。
- GPGME 通过 `gpgconf --list-components` 解析引擎路径，同一前缀使它取到只读的 `/bin/gpg` 并全量报 `GPGME: Invalid crypto engine`。配方在构建目录内生成 `gpgconf` 包装脚本，只改写目录列表中的 `//` 安装前缀，其余调用原样 `exec`（任何缓冲转发都会让 GPGME 的 gpgconf 会话死锁），并在 `make check`/`make install` 时把该目录置于 PATH 首位。
- `package()` 必须在源码树内执行 `make install`：`Autotools.install()` 的默认 cwd 是 `basic_layout` 的 generators 目录（`build-release`），其中没有 Makefile，会报 `No rule to make target 'install'`。CI worker 上迁出目录的父目录可进入但不可读，shell 若直接以该目录为 cwd 会报 `getcwd: cannot access parent directories`，libtool 因而把 `libgpgmepp.la` 的 relink 记成 `(cd ; $SHELL /libtool ...)`，`make install` 在 `install-libLTLIBRARIES` 失败。配方改为从 Conan 构建目录 `cd` 到绝对路径并 `export PWD`（不用 `make -C`），并让 libtool 的 `pwd` 在 getcwd 失败时回退到 `$PWD`；安装前若 `.la` 里仍是空的 `cd`，改写成该库所在目录和绝对 `libtool` 路径。安装同样需要 GnuPG 运行时闭包与包装脚本。
- `make check` / `make install` 结束时用带超时的 `gpgconf --kill`，再按 `/proc` 命令行 SIGKILL 本构建树的 `gpg-agent` 与 `dirmngr` 并删掉套接字，避免 CI 步骤在安装失败后空等到超时。
- 顶层 `make install` 会进入未跑的 `tests/json` 并重建 `pubring-stamp`：该规则先 `gpgconf --kill all` 再 `gpg --import`，而打包的 gpg 不能自启动 agent，导入以 Error 2 结束。这些钥匙环不是安装产物。`package()` 只在 `src` 和 `lang` 里执行 `make install`（不把 `SUBDIRS` 放进 make 命令行，否则会传给 `lang/` 并跳过 cpp 与 qt）。
- `tests/json`（`t-json`）不纳入 `make check`：它经 GPGME 的 SPAWN 协议驱动 `gpgme-json -s`，本机子进程 fork 后不替换映像并持续占用 CPU（4 秒采样 utime +115 jiffies，`/proc/<pid>/exe` 仍指向 `t-json`），父进程在 gpgme 事件循环等待输出管道 EOF，套件不返回；去掉 `gpgconf` 包装则立即在 `tests/gpg/t-support.h:219` 报 `Invalid crypto engine`。该项按未执行申报，不写成通过。

真机结果（2026-10-10，复现 CI 的缓存位置，并用 `LD_PRELOAD` 让路径含 `gpgme-1.24.2-src` 时 `getcwd` 返回 EACCES，shell 出现与 CI 相同的 `shell-init: getcwd: cannot access parent directories`）：`CONAN_HOME=/storage/Users/currentUser/work/psj/ch-gpg13444fix`（HMDFS）。源码目录 `AF_UNIX.bind()` 返回 EPERM 后，日志出现 `relocating in-tree build to /data/storage/el2/base/cache/gpgme-1.24.2-src`。`conan create --build=gpgme/1.24.2` 退出码 0；上游 37 项中 36 项执行且全部通过——`All 3 tests passed`、`All 28 tests passed`（含 `initial.test`/`final.test`）、`All 9 tests passed`，逐条 `PASS:` 40 行、`FAIL:` 0 行、`SKIP:` 0 行。`tests/json` 的 `t-json` 未执行。安装得到 `libgpgme.so.11.33.2`、`libgpgmepp.so.6.21.2`、`libqgpgmeqt6.so.15.6.2` 以及对应头文件和 CMake 配置，包内无 `.la`。两个原生消费者 2/2 通过：`gpgme version: 1.24.2` / `gpgme engine info OK` 与 `Gpgmepp and QGpgmeQt6 linked; GPGME 1.24.2; OpenPGP protocol 1; error=0`。结束后该构建树没有残留 `gpg-agent` / `dirmngr`。
