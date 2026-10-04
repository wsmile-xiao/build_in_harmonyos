# kea-dhcp4

ISC Kea 的 **kea-dhcp4**（DHCPv4 服务器守护进程），适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`kea-dhcp4` 是 Kea 的 DHCPv4 服务器：读取 JSON 配置（`subnet4`/`pools`/options/
`lease-database`/`hooks`/`dhcp-ddns` 等），在指定接口上监听 UDP 67 端口，应答
DISCOVER/REQUEST/RELEASE/INFORM 等报文，支持 memfile 与 mysql/pgsql 租约后端、
hook 扩展、控制通道（Unix socket / HTTP）与租约文件压缩（kea-lfc）。

命令行接口：

- `-v` / `-V`：版本号 / 扩展版本（含链接库信息）
- `-W`：输出构建期生成的 configure 报告
- `-t <cfg>`：配置校验（check-only，完整走配置解析链但不打开 socket）
- `-c <cfg>`：按配置启动服务器（真实监听，需相应权限）
- `-d`：调试模式；`-p`/`-P`：测试用非标准端口

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/bin/dhcp4/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：上游 `SBINDIR`（本包按 Conan 约定安装到 `bin/kea-dhcp4`）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件，须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（`CRYPTO_DEP`） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带服务器运行期加载的 20 个 Kea 共享库（`libkea-*.so*`，全树运行时
集合，含 soname 名与全版本名），因此安装后无需额外的 Kea 运行库即可直接执行。

## OHOS 适配要点

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`，使
   `iface_mgr_linux.cc` / `pkt_filter_lpf.cc` 等 Linux 后端源码被选中
   （补丁 0001）。
2. **UAPI 头冲突**：OHOS 的 `linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → 包含 netlink 头时用 define-guard 重命名内核侧
   定义（`__linux__ && !__GLIBC__` 守卫，无需平台宏，补丁 0002）。
3. **configure 期脚本 execve**：OHOS 内核拒绝对 shebang 脚本的 execve（与可执行位
   无关）→ `scripts/env.sh`、`grabber.py`、`config-report.sh`、`mk_cfgrpt.sh`
   改由解释器前缀调用（补丁 0003/0004；`-W` 输出的 configure 报告正来自这条
   生成链，等于对修补链做了运行时端到端校验）。
4. **netlink bind 回退**：OHOS 沙箱对 AF_NETLINK 只放行 `socket()`、拒绝
   `bind()` → IfaceMgr 接口检测回退 `getifaddrs()`（补丁 0005；DHCPv4 服务器
   的测试会构造生产 `IfaceMgr` 检测路径，ctrl_dhcp4_srv / http_control_socket
   等用例需要它）。
5. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
6. **Meson 调用面**：conan 的 meson 包 `bin/meson` 是 shebang 包装脚本，
   OHOS 拒脚本 execve → 一律 `sh <meson> setup/compile/test`；`meson compile`
   限并发 `-j 8`（沙箱进程配额，防 posix_spawn EAGAIN）。
7. **soname 物化与 0 字节自愈**：/storage 沙箱拒符号链接 → compile 后以复制
   方式物化 `libkea-X.so.N` 名（`_materialize_sonames`，幂等）；package()
   对 0 字节落盘做三重补拷复核（有界重试，仍为 0 则打包失败）。
8. **Meson 工具链**：需同时使用 `PkgConfigDeps`（依赖 `.pc`）与
   `MesonToolchain`；配置期 `cpp.run()` 探针要求 host 共享依赖在
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径。
9. **CLI 进 bin/ + 登记**：可执行文件按 Conan 约定落 `bin/kea-dhcp4`，并提供
   软件级 `commands.json`（R38）与运行环境 PATH。
10. **测试侧平台适配（补丁 0006-0011）**：`/tmp` 只读 → 上游测试沙箱与 HTTP
   控制通道 config-write 用例的路径改建于 `TMPDIR`（补丁 0006/0010，sandbox
   补丁与 kea-dhcp6 配方逐字节同源）；hmdfs 用户存储不承载 AF_UNIX pathname
   socket → 控制通道用例以服务器同款 bind 操作探测后整体跳过（补丁 0007-0009，
   55 例控制通道服务器用例 + 2 例配置 commit 用例；常规 Linux 上探测恒真、
   跳过永不触发）；`meson test()` 直接 spawn shell 套件脚本死于 shebang
   execve → 套件经 `sh` 运行（补丁 0011，与 0003/0004 同一内核特性）。

## 上游测试

`src/bin/dhcp4/tests/meson.build` 注册 2 个测试；本包在 `build()` 内**两个套件
全部真实执行**：

| 套件 | 用例 | 说明 |
|------|------|------|
| `kea-dhcp4-tests` | 948 宏计 / 1024 运行期 | 28 个源文件（24 个含用例）编译的单个 gtest 可执行文件：报文分类、配置解析（148）、服务器核心（128）、HTTP 控制 socket（84）、DORA（82）、vendor options（63）、控制通道服务器（55）、hooks（55）、FQDN（53）等；真机运行期注册 1024 用例 / 29 套件（TEST_P 实例化展开）；其中 2 个上游 `DISABLED_` 用例由 gtest 标记不运行 |
| `dhcp4_process_tests.sh` | 14 个子用例 | 以真实 kea-dhcp4 进程验证 pid 文件互斥、SIGHUP 动态重配置、SIGTERM/SIGINT 优雅停机、版本/日志变量、LFC 定时触发两轮、6 项语法校验、密码脱敏（全部 `interfaces: []`，不开 socket） |

本版本实测：**两套件 1038 例全量实跑——981 通过（gtest 967 + shell 14/14）、
57 例平台性 SKIP、0 失败；全树编译链接零错误（1433/1433）。**

## test_package（消费者视角 + 鸿蒙特有用例）

`conan create` 的 test 阶段真实编译并执行 3 个测试（CMake + `find_package(kea-dhcp4)`）：

| 测试 | 检查项 | 内容 |
|------|------|------|
| `test_dhcp4.py` | 21 | 版本/扩展版本/配置报告输出（`-v`/`-V`/`-W`）、命令行错误路径、`-t` 配置校验正反路径（最小配置通过；坏 JSON/缺 Dhcp4 元素/文件不存在被拒） |
| `test_ohos_platform`（**鸿蒙特有**） | 11 | 包内 `bin/kea-dhcp4` 的 OHOS 平台 ABI 特征：ELFCLASS64 / `EM_AARCH64` / `ET_DYN`(PIE)、`DT_NEEDED` 链接 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so` 且非 GNU `libstdc++`，另含 DT_STRSZ/NEEDED 解析守卫 |
| `test_ohos_runtime`（**鸿蒙特有**） | 6 | OHOS 加载器下的运行时闭包：`DT_NEEDED` 的 Kea 库全部随包分发、≥20 个去重 `libkea-*.so*` 全部 `dlopen(RTLD_NOW)` 成功、真实执行 `kea-dhcp4 -v` 输出 `3.0.3` |

鸿蒙特有测试用例 **2 个**，实测 **2/2 通过（17/17 项检查：平台 ABI 11 + 运行时闭包 6）**。

## 使用

```bash
conan install --requires=kea-dhcp4/3.0.3 -pr:h=<ohos-aarch64 profile>

# 版本
kea-dhcp4 -v
kea-dhcp4 -V

# 配置校验（不打开 socket，无需特权）
kea-dhcp4 -t /path/to/kea-dhcp4.conf

# 按配置启动（真实监听 UDP 67，需相应权限）
kea-dhcp4 -c /path/to/kea-dhcp4.conf
```
