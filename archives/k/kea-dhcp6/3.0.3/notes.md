# kea-dhcp6 3.0.3 适配笔记

## 编译环境
- 构建系统: meson（Kea 3.0 起由 Autotools 迁移；顶层 `meson.build`）
- 编译日期: 2026-10-04
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26，aarch64-linux-ohos，libc++，C++17）
- 工作副本: `wt-kea-dhcp6`（分支 `feat/kea-dhcp6-3.0.3`，基线 `origin/main`）
- 真机构建树: `/storage/Users/currentUser/.conan2/p/b/kea-h0ef16bf7ff643/b`（真实 meson 树，全量实跑验证）
- 状态: built

## 编译步骤

```bash
# 1) Conan 生成 Meson 工具链（PkgConfigDeps + MesonToolchain）
conan install . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -of=<of>

# 2) 配方 build() 内真实执行的步骤（经 sh 调用 meson 包装脚本，见问题 #11）
sh "<meson 包>/bin/meson" setup --native-file <of>/build-release/conan/conan_meson_native.ini \
    <of>/build-release <src> --prefix=/
sh "<meson 包>/bin/meson" compile -C <of>/build-release -j 8
# _materialize_sonames()（配方内自动，见问题 #12）
sh "<meson 包>/bin/meson" test -v --timeout-multiplier 4 -C <of>/build-release \
    kea-dhcp6-tests dhcp6_process_tests.sh

# 3) 配方固化与官方验证
ohc-run.py refresh-patch --auto kea-dhcp6 3.0.3
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
ohc-run.py conan-verify kea-dhcp6 3.0.3
ohc-run.py finish kea-dhcp6 3.0.3 built
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `meson.build:186:4: ERROR: Problem encountered: Unsupported system "harmonyos".` | OHOS 上 `platform.system()` 返回 HarmonyOS，meson 据此报告 host system=`harmonyos`；Kea 白名单只有 linux/freebsd/netbsd/openbsd/sun/darwin | 补丁 `0001`（+7/-1）：顶层把 `SYSTEM == 'harmonyos'` 归一化为 `'linux'`（家族补丁，与 kea-hook-* 逐字节一致） |
| 2 | 编译期 `iface_mgr_linux.cc:40: error: redefinition of 'sockaddr_storage'` | OHOS sysroot 的 `linux/socket.h`（bionic 派生）与 musl `sys/socket.h` 都定义 `struct sockaddr_storage` | 补丁 `0002`（+14/-1）：包含 netlink 头前 define-guard 重命名内核侧定义，守卫 `__linux__ && !__GLIBC__`（不用平台宏） |
| 3 | `meson.build:477 ERROR: Boost TLS support broken`（`use of undeclared identifier 'pthread_setcancelstate'`） | OHOS musl `pthread.h` 不声明该函数，boost `sp_thread_sleep.hpp` 无条件调用 | `generate()` 注入 boost 官方逃生宏 `-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE` |
| 4 | `Checking if "LOG4CPLUS_INITIALIZER_H" runs: NO (127)` → `Unknown variable "log4cplus"` | meson 特性探针编译并运行；host 共享依赖 `liblog4cplus.so.9` 不在配置期 `LD_LIBRARY_PATH` | `generate()` 把各 host 依赖 `cpp_info.libdirs` 追加进 `LD_LIBRARY_PATH`，`save_script("conanbuildenv-kea-runtime")` |
| 5 | configure 期 `env.sh` / `grabber.py` / `config-report.sh` / `mk_cfgrpt.sh` 直接执行报 Error 126 | OHOS 内核拒绝 shebang 脚本 execve（与可执行位无关） | 补丁 `0003`（+10/-5，顶层 meson.build 脚本变量改为解释器前缀数组）+ `0004`（+2/-2，cfgrpt） |
| 6 | `Unknown linker(s): [['llvm-ar']]`（configure 期首个错误） | meson 对 clang 默认裸名探测静态链接器，MesonToolchain 未写 `ar/ranlib`，OHOS 只按绝对路径解析 | `generate()` 从 `tools.build:compiler_executables` 推导同目录 `llvm-ar`/`llvm-ranlib` 写入 `tc.binaries` |
| 7 | 沙箱类测试崩溃（mkdtemp 返回 NULL 后解引用） | 上游 testutils sandbox 默认 `P_tmpdir`（/tmp），鸿蒙 app 沙箱 /tmp 只读 | 补丁 `0006`（+16/-3，`src/lib/testutils/sandbox.h`）：建沙箱目录前先取 `TMPDIR`，无则回退原路径 |
| 8 | unix 命令通道用例成组失败（45 个挂） | 鸿蒙用户存储是 hmdfs 挂载，`bind()` AF_UNIX 路径名套接字返回 EPERM——服务器 control-socket 无法建立 | 补丁 `0007`（+47/-2，dhcp6_test_utils）：新增"与服务器同型"的 bind 探针（`unixControlSocketsUsable()`）；补丁 `0008`（+10/-1）在 `CtrlChannelDhcpv6SrvTest` 直接 socket 组与继承 socket 组按探针跳过；补丁 `0009`（+20/-2）跳过 2 个配置含 unix control socket 的 config-commit 用例 |
| 9 | HTTP 控制通道配置写测试失败 | 测试把配置文件写到 /tmp（只读） | 补丁 `0010`（+15/-5，http_control_socket_unittest.cc）：路径建在 TMPDIR（回退 /tmp） |
| 10 | `dhcp6_process_tests.sh` 执行报 Error 126 | OHOS 内核拒绝 shebang 脚本 execve | 补丁 `0011`（+7/-2，src/bin/dhcp6/tests/meson.build）：test() 的 command 改为经 sh 执行 |
| 11 | conan 的 meson 包装脚本（`bin/meson` shebang 脚本）直接执行报 Error 126 | 同上 execve 限制 | `build()` 经 `sh "<meson 包>/bin/meson"` 调用（`_meson()` 前缀，家族配方同款） |
| 12 | `kea-dhcp6-tests` / 服务器启动报 `Error loading shared library libkea-X.so.N`（exit 127，疑似链接竞态） | OHOS /storage 沙箱拒绝符号链接（ln -s → EPERM）：meson 的 soname 名只以符号链接发布，链接名文件根本不存在，NEEDED 查找全部落空 | `build()` 在 compile 后 `_materialize_sonames()`：以复制方式物化 soname 名（幂等；真机实测物化 23 个，含闭包外库）。shell 套件的 `server_pid_file_test` 失败（服务器起不来）同为该根因，物化后全绿 |
| 13 | `meson compile` 中途 posix_spawn EAGAIN | OHOS 沙箱限制并发进程数，ninja 默认按 20 核并发（~45 个活动 spawn） | `meson compile -j 8`（家族配方实测值） |
| 14 | `dhcp6_process_tests.sh` 被 meson 判超时（30s 默认预算） | 套件按 30s 通用预算，设备上单测最长约 112s（多组 kea-dhcp6 进程串行启动） | `meson test --timeout-multiplier 4`（家族配方式） |
| 15 | 官方 conan-verify 的 G2 报 `conan create` 失败：test_package 的 `test_ohos_platform` 输出 `DT_NEEDED closure (0 entries)` 并 FAIL（libc.so / libc++_shared.so），但同一二进制 `readelf -d` 明明列出 19+2 条 NEEDED | 探针把 `.dynstr` 读进固定 64 KiB 缓冲并把 `strsz` 截到上限；包内 `bin/kea-dhcp6` 的 `.dynstr` 实测 **96373 字节**，所有 NEEDED 名字偏移（96006~96365）都在截断界外，被 `d_un.d_val < strsz` 过滤 → 静默解析出 0 条（假阴性） | 两个鸿蒙探针（`test_ohos_platform.c` / `test_ohos_runtime.c`）改为按 `DT_NEEDED` 偏移**逐条点读**字符串表（单名 ≤255 字节），删除固定缓冲与 `STRTAB_SIZE` 上限；platform 探针在 `DT_STRTAB/DT_STRSZ` 不可解析时打印显式警告。修复后真机实测：platform 8/8（19 条闭包全解析）、runtime 全过（40/40 dlopen + `-v` 出 3.0.3）、消费者契约 16/16 |

> 平台差异 1-6 与家族已合入配方一致（补丁 0001-0005 逐字节复用，md5 对账通过）；
> 7-15 为本包首曝或本包测试面复现，均以真机原始输出取证（见 `logs/` 同级记录）。

## 源码修改

| 补丁 | 文件 | 行数 | 内容 |
|------|------|------|------|
| 0001-meson.build.patch | `meson.build` | +7/-1 | harmonyos → linux 平台名归一化（家族） |
| 0002-src-lib-dhcp-iface_mgr_linux.cc.patch | `src/lib/dhcp/iface_mgr_linux.cc` | +14/-1 | netlink 头包含期 `sockaddr_storage` define-guard（家族） |
| 0003-meson.build.patch | `meson.build` | +10/-5 | configure 期脚本经解释器执行（家族） |
| 0004-src-lib-process-cfgrpt-meson.build.patch | `src/lib/process/cfgrpt/meson.build` | +2/-2 | mk_cfgrpt.sh 经 /bin/sh（家族） |
| 0005-src-lib-dhcp-iface_mgr_linux-getifaddrs-fallback.patch | `src/lib/dhcp/iface_mgr_linux.cc` | +82/-3 | netlink 被沙箱拒绝时 getifaddrs() 回退（家族） |
| 0006-src-lib-testutils-sandbox.h.patch | `src/lib/testutils/sandbox.h` | +16/-3 | 沙箱目录优先 TMPDIR（/tmp 只读） |
| 0007-src-bin-dhcp6-tests-dhcp6_test_utils-unix-socket-check.patch | `src/bin/dhcp6/tests/dhcp6_test_utils.{cc,h}` | +47/-2 | AF_UNIX 路径名 bind 探针 + 套件跳过助手 |
| 0008-src-bin-dhcp6-tests-ctrl_dhcp6_srv_unittest-skip-unix-channel.patch | `src/bin/dhcp6/tests/ctrl_dhcp6_srv_unittest.cc` | +10/-1 | 45 个 unix 通道用例按探针跳过 |
| 0009-src-bin-dhcp6-tests-config-commit-skip-unix-control-sockets.patch | `src/bin/dhcp6/tests/config_parser_unittest.cc` + `get_config_unittest.cc` | +20/-2 | 2 个 unix control socket 配置用例按探针跳过 |
| 0010-src-bin-dhcp6-tests-http_control_socket_unittest-tmpdir.patch | `src/bin/dhcp6/tests/http_control_socket_unittest.cc` | +15/-5 | 配置写路径改用 TMPDIR |
| 0011-src-bin-dhcp6-tests-meson.build-shell-test-via-sh.patch | `src/bin/dhcp6/tests/meson.build` | +7/-2 | shell 套件经 sh 执行 |

补丁均不含平台宏（PF5 通过）；0001-0005 与家族 kea-hook-ha 同名补丁逐字节一致，0006-0011 按 staged-diff 生成并逐枚在纯净源码树按序验证可应用。

## 依赖版本

| 依赖 | 版本 | 类型 | 说明 |
|------|------|------|------|
| boost | 1.85.0 | 强制 | 1.90/1.91 缺 `boost/interprocess/...`、`circular_buffer` 等 Kea 强制头 |
| log4cplus | 2.2.0.1 | 强制 | Kea 日志后端（`shared=True`，配置期运行探针需 LD_LIBRARY_PATH） |
| openssl | 3.5.8.1 | 强制 | 默认 `crypto=openssl`（CRYPTO_DEP） |
| gtest | 1.17.0.1 | test_requires | `-Dtests=enabled` |
| meson | 1.11.0 | tool_requires | Kea 需 ≥1.10（boost 无 `libboost_system`，走 header-only 模块回退） |

## 包内容与运行期依赖

`kea-dhcp6` 可执行文件（`bin/kea-dhcp6`）+ 20 个 Kea 共享库（`lib/libkea-*.so*`：
asiolink、cc、cfgrpt、config、cryptolink、database、dhcp、dhcp_ddns、dhcpsrv、dns、
eval、exceptions、hooks、http、log、log-interprocess、process、stats、tcp、util，
含物化的 soname 名）。上游 `INSTALL_RPATH` 指向构建机 prefix，Conan 包改用
`cpp_info.libdirs=["lib"]` 让生成的 run 环境提供 `LD_LIBRARY_PATH`。

## 上游测试（本次实测：2/2 套件，用例级 979 跑 / 932 过 / 47 平台跳过 / 0 挂）

- `kea-dhcp6-tests`（gtest，31 套件）：965 例实际执行，918 通过、47 跳过、0 失败
  （源码另有 2 个上游 `DISABLED_` 用例按 gtest 语义不执行）；49.08s。
  47 个跳过 = 45 个 unix 命令通道用例（补丁 0008）+ 2 个 config-commit 用例（补丁 0009），
  均为 hmdfs 拒绝 AF_UNIX 路径名 bind 的平台性不支持，非逻辑失败。
- `dhcp6_process_tests.sh`（进程级 shell 套件）：14/14 通过；112.40s
  （多组真实 kea-dhcp6 进程串行启动，需 `--timeout-multiplier 4`）。
- meson 汇总：**Ok: 2 / Fail: 0**，TEST_RC=0。

## 鸿蒙特有测试用例（test_package，2 个用例，实测 2/2 通过）

| 用例 | 文件 | 测试用例数 | 覆盖内容 |
|------|------|------|----------|
| `test_ohos_platform` | `test_package/test_ohos_platform.c` | 8 | 包内 `bin/kea-dhcp6` 的 OHOS 平台 ABI 特征（ELFCLASS64 / `EM_AARCH64` / `ET_DYN` PIE；`DT_NEEDED` 含 musl `libc.so` 且不含 glibc `libc.so.6`；含 `libc++_shared.so`） |
| `test_ohos_runtime` | `test_package/test_ohos_runtime.c` | 6 | OHOS 加载器下的运行时闭包（DT_NEEDED 的 Kea 库全部随包分发；20 个 `libkea-*.so*` 全部 `dlopen(RTLD_NOW)` 成功；真实执行 `kea-dhcp6 -v` 输出 `3.0.3`） |

另含通用消费者测试 `test_kea_dhcp6.py`（16 个测试用例；真实执行器：逐例 TEST PASS/FAIL +
末行 TEST SUMMARY，任一失败退出码 1）：版本输出（`-v`/`-V`）、
构建配置报告（`-W` 含 "Kea source configure results"）、语法检查 `-t` 三个路径
（合法配置 `{"Dhcp6":{"subnet6":[]}}` 退出 0；非法 subnet 报 "Invalid subnet syntax"；
缺失文件报 "Unable to open file"）、非法选项 `-z` 的拒绝与 usage 文本，并校验各次
运行 stderr 无 "Error loading shared library"。

## 服务器 CLI 契约（真机实测，消费者测试的锚点）

| 调用 | 结果 |
|------|------|
| `kea-dhcp6 -v` | 输出 `3.0.3`，RC=0 |
| `kea-dhcp6 -V` | 输出 `3.0.3 (3.0.3 (tarball))` + 详情，RC=0 |
| `kea-dhcp6 -W` | 输出 57 行配置报告（首行 `Kea source configure results:`，含 `Version: 3.0.3`），RC=0 |
| `kea-dhcp6 -t <合法>` | `{"Dhcp6":{"subnet6":[]}}` → RC=0（注意：3.x 中带 pools 的 subnet 必须含 `"id"`，否则报 `missing parameter 'id'`） |
| `kea-dhcp6 -t <非法 subnet>` | RC=1，`Invalid subnet syntax (prefix/len expected)` |
| `kea-dhcp6 -t <不存在文件>` | RC=1，`Syntax check failed with: Unable to open file` |
| `kea-dhcp6 -z` | RC=1，`unrecognized option: z` + `Usage: kea-dhcp6 ...` + `Kea DHCPv6 server, version 3.0.3 (stable)` |

## R37 / R38

- R37：官方 main 中不存在 kea-dhcp6 既往版本（`git ls-tree HEAD archives/k/kea-dhcp6` 为空），
  本包为 3.0.3 首发，版本号按任务卡。
- R38：本包产物是可执行文件，已在软件级别目录提供 `archives/k/kea-dhcp6/commands.json`
  （`type=tool`、`binary=true`）；包内可执行文件按 Conan 约定落在 `bin/`。
---

**编译结束**: 2026-10-04
**最终状态**: built
