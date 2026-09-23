# ncrack 0.7 适配笔记

## 编译环境

- 构建系统: autotools（`configure.ac` + **手写** `Makefile.in`，非 automake；dist 已带 2019 版 Autoconf 2.69 生成的 `configure`，无需 autoreconf）
- 平台任务: contrib-5760（ncrack 0.7），claimer Ember5843
- 目标平台: HarmonyOS PC arm64（`os=OHOS arch=armv8 compiler=clang 15 libc++`），本机原生构建（build = host）
- 编译器: clang/clang++ 15.0.4（`.harmonybrew/bin`）
- 依赖: `openssl/1.1.1w`（制品仓已发布）
- 上游: https://github.com/nmap/ncrack tag `0.7`（无 v 前缀）= commit `dc570e7e`；GitHub API 实证非 fork、未归档
- 源码 sha256: `f3f971cd677c4a0c0668cb369002c581d305050b3b0411e18dd3cb9cc270d14a`（本机与设备 `sha256sum` 逐字符一致）
- 状态: built

## 源码面貌（摸底结论）

- 主体 C++：顶层 `ncrack.cc` 等 30 余个 `.cc`；内置三个子项目 `nbase/`（C 库）、`nsock/`（C 库，事件循环）、`opensshlib/`
- 语言预检（R47）：task=cpp，detected=cpp，主体占比 73%（184 个源文件：c 135 / cpp 48 / bash 4 / perl 1）
- `configure.ac` **自带** `--with-libpcap=no`（注入 `ac_configure_args`）→ 不需要 libpcap
- OpenSSL 在 configure 里是"可选"（找不到只告警禁用），但源码层面是**硬依赖**：
  `ntlmssp.cc` 无条件 `#include <openssl/hmac.h> / <openssl/md4.h> / <openssl/md5.h>`，
  只有 `crypto.cc` 用 `#if HAVE_OPENSSL` 守卫。因此必须 `--with-openssl` 提供头与库。
- 无顶层 `check`/`test` 目标；上游回归套件在 **`nsock/tests/`**（7 个测试 TU：basic/timer/logs/connect/ghlists/ghheaps/cancel + `run_tests.sh`），
  由 `nsock/src/Makefile.in` 的 `check:` 目标驱动。上游自己的 CI（`.travis.yml`）只跑 `./configure && make`，不跑测试。

## 编译步骤

```sh
# 1) 取源码（官方 tarball，sha256 见上）
# 2) configure（关键：CONFIG_SHELL=zsh + stdin=/dev/null，显式双三元组）
CONFIG_SHELL=/usr/bin/zsh SHELL=/usr/bin/zsh \
  ./configure \
    --build=aarch64-unknown-linux-musl --host=aarch64-unknown-linux-gnu \
    --prefix=/ --with-libpcap=no --with-openssl=<openssl/1.1.1w 包目录> < /dev/null
# 3) make -j1
# 4) make -j1 check（在 nsock/src：上游回归套件）
# 5) make -j1 install DESTDIR=<package_folder>
```

配方内 OHOS 分支的关键机器码：`_resolve_shell()`（zsh 优先、bash 兜底）、
`_configure_args()`（双三元组 + prefix=/ + with-openssl）、`_run_ohos()`（导出 SHELL/CONFIG_SHELL 并 `< /dev/null`）。
因 `Makefile.in` 不是 VPATH 感知（`SRCS` 是裸文件名），构建在 **build 目录内的源码副本**中进行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `./configure[557]: 7<&0 : bad file descriptor` | autoconf 2.69 用 `exec 7<&0` 保存 stdin；OHOS `/system/bin/sh`（toybox）不支持多位数 fd 重定向 | 设 `CONFIG_SHELL=/usr/bin/zsh`（系统镜像自带，5.9，musl 构建）；configure 自举块在 fd-7 行之前，会自动 re-exec 成 zsh，子目录递归同样继承 |
| 2 | 换 zsh 后仍失败：`./configure:557: 0: bad file descriptor` | worker/CI 执行 job 时 **fd 0 是关闭的**，`exec 7<&0` 需要有效 stdin | 调用 configure 时显式 `< /dev/null`（配方内 `_run_ohos` 统一追加） |
| 3 | `make` 报 `ntlmssp.cc:166: fatal error: 'openssl/hmac.h' file not found` | configure 找不到 OpenSSL 时只告警禁用，但该文件无条件 include openssl 头 | `--with-openssl=<openssl/1.1.1w 包目录>` 显式启用（1.1.1w 与 2019 年的 ncrack 同代，避免 OpenSSL 3.x 的 API 变更风险） |
| 4 | 设备无 `cc`/`c++` | 仅安装了 clang | configure 显式 `CC=clang CXX=clang++`（配方经 AutotoolsToolchain 提供） |
| 5 | `config.status:601: permission denied: ./confXXXXXX/subs1.awk` → `could not setup config files machinery` | configure 与 config.status 都用 `(umask 077 && mktemp -d "./confXXXXXX")` 建临时目录，得到 **2700（drwx--S---）**；而 **hmdfs 按组判目录通行**（本机所有目录都是 `drwxrws--x`），组无 x → 该目录不可穿越 → 其内读写全部 EACCES。`chmod g+rx` 实测无效（hmdfs 不认 Unix 权限位） | 把 **四个** configure（顶层 + nbase + nsock/src + opensshlib）的 `umask 077` 全部改写为 `umask 022`（022 下建出 `drwxr-s--x`，可穿越）。只改顶层不够：子目录仍报 `configure: error: ./configure failed for nbase` |
| 6 | `checking openssl/opensslv.h usability... no` → `*** OpenSSL headers missing ***`（opensshlib） | 顶层 `--with-openssl=DIR` 只设置顶层 configure 内部的 CPPFLAGS；conan 的 AutotoolsToolchain **不注入** CPPFLAGS/LDFLAGS（实测 env 脚本为空），子目录 configure 因而找不到 OpenSSL，而 opensshlib 的检查是**硬报错** | 追加 `--with-ssl-dir=<openssl 包目录>`：opensshlib 用自己的 `--with-ssl-dir` 选项（帮助文案误写为 `--with-openssl=PATH`）设置 `-I<dir>/include`、`-L<dir>/lib`，其 `LIBS=-lcrypto` 链接探测随之通过；顶层只对未知选项告警并原样转发给子目录 |
| 8 | `ld.lld: error: duplicate symbol: umac_ctx`（link 阶段） | opensshlib 的 Makefile 用同一份 `umac.c` 加 `-DUMAC_128` 再编出 `umac128.o`，两个 TU 都定义全局 `umac_ctx`（`struct umac_ctx { ... } umac_ctx;` 无初值 = C 的 tentative definition）；clang≥11 默认 `-fno-common` + ld.lld 报重复符号 | **两步走**：①先加 `-fcommon`（设备侧通过）；②但 CI worker 的编译标志传播路径不同，同一配方在 CI #45813 仍复现该重复符号 → 改为**从根上消除**：补丁 `0001-opensshlib-umac-drop-unused-global.patch` 删掉这个**从未被使用**的全局变量（grep 实证：其余 `umac_ctx` 全是类型 `struct umac_ctx`），两 TU 只剩各自 TU 内的类型名，重复符号在任何 `-fcommon` 设置下都不可能再出现。`-fcommon` 保留作为年代语义兜底 |
| 7 | `crypto.cc:576: error: ISO C++17 does not allow 'register' storage class specifier`（23 处） | ncrack 0.7（2019）早于 C++17 移除 `register`，而平台 profile 声明 `cppstd=17` | `tc.extra_cxxflags.append("-std=gnu++14")`（本仓 robin-map/riscv64-elf-gdb 同款写法）；ncrack 是应用而非库，C++ 标准属内部实现细节，**不改上游源码** |

## 源码修改

**1 个补丁**：`patches/0001-opensshlib-umac-drop-unused-global.patch`
（删除 `opensshlib/umac.c` 中未被使用的文件作用域全局 `umac_ctx`，消除 `umac.o`/`umac128.o`
两 TU 的重复符号；语义等价——该变量无任何引用，删的是定义不是类型）。
其余 7 项问题均在构建期机器码内解决，未改动上游源码。

## 依赖版本

- `openssl/1.1.1w`（制品仓 ohpcd 已发布；ncrack 0.7 的 NTLM/RDP 认证路径所需）

## 验证结果（设备实机实测，2026-09-13）

```text
$ conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
...
ncrack/0.7: package(): Packaged 3 files: ncrack, ncrack-services, COPYING
ncrack/0.7: package(): Packaged 1 '.1' file: ncrack.1
ncrack/0.7: Package 'fa0953374eb541d5297b4602102750d331f26fb0' created
--- ncrack --version ---
Ncrack version 0.7 ( http://ncrack.org )
Modules: SSH, RDP, FTP, Telnet, HTTP(S), Wordpress, POP3(S), IMAP, CVS, SMB, VNC, SIP,
         Redis, PostgreSQL, MQTT, MySQL, MSSQL, MongoDB, Cassandra, WinRM, OWA, DICOM
--- local scan of a closed port (127.0.0.1:9, rdp module) ---
Ncrack done: 1 service scanned in 3.00 seconds.
Ncrack finished.
test_ncrack.sh: PASS
```

八门禁（`ohc-run.py conan-verify ncrack 0.7`）：**G0/G1/G2/G3/G4 + L2/L4/L5 全部 PASS，VERIFY_RC=0**。
W3 本地 CI 模拟：**PASS**（`.ci-result.json` exit_code=0）。收尾：`ohc-run.py finish ncrack 0.7 built` → EXIT_CODE 0。

上游测试面（实数实测）：nsock 回归套件 7 个用例 TU（+`tests_main.c`）在 `make check` 中**全部编译通过**；
`run_tests.sh` 执行需 `ncat`（Nmap 项目另一工具，设备与 CI 均无）→ 打印 `Skipping nsock tests.`，**执行数为 0**；
上游自身 CI（`.travis.yml`）只跑 `./configure && make`。执行级验证由 test_package 的真实运行承担。

## Phase 2 构建记录（设备实机，mailbox 通道）

1. 第 1~3 轮：configure 卡在 shell/fd（见问题 1/2）与 opensshlib 的 OpenSSL（问题 6）
2. 第 4~6 轮：编译通过、链接报 `umac_ctx` 重复符号（问题 8）→ `-fcommon`
3. 第 8~9 轮：包创建成功；test_package 执行被 E549 拦截（问题 E549）→ 配方内自签名
4. 第 10~11 轮：数据文件定位（`$NCRACKDIR`）修正后 **test_ncrack.sh: PASS**
5. `conan-verify` 首轮暴露 source 下载的两处不确定性（问题见下），改为显式绝对路径后 **八门禁全绿**
6. `finish ncrack 0.7 built`：W3 PASS，产出 `.ci-result.json` / `.conan-verified` / `.build-closed`

**编译结束**: 2026-09-13
