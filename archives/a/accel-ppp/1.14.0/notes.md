# accel-ppp 1.14.0 适配笔记

## 编译环境
- 构建系统: CMake（初始化脚本首次误判为 autotools）
- 编译日期: 2026-08-18
- 编译器: clang 15.0.4 (OHOS aarch64)
- 状态: published（原生 PPP 服务端已成功构建，依赖 libucontext 提供 getcontext/setcontext）

## 编译步骤

1. 从上游 Git 标签 `1.14.0` 获取源码，验证提交为 `048d31cb446879e0d1a1471b4ab99135a92bf289`。
2. 使用 Conan OHOS armv8 profile 安装依赖（openssl/3.5.6.1.1、pcre2/10.45.1.1、libucontext/1.5.2）。
3. 配置：`cmake -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake -DBUILD_PPTP_DRIVER=OFF -DBUILD_IPOE_DRIVER=OFF -DBUILD_VLAN_MON_DRIVER=OFF -DLOG_PGSQL=OFF -DSHAPER=OFF -DRADIUS=OFF -DNETSNMP=OFF -DLUA=OFF`
4. 构建：`cmake --build` → 全部模块编译链接成功，`accel-pppd` 与 `accel-cmd` 产物生成。
5. 冒烟测试（详见 reports/test-report.md）：--version / --help / accel-cmd --help / 缺配置失败关闭 / 最小配置守护进程运行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `sockaddr_storage` 重定义（27+ 文件） | OHOS musl `sys/socket.h` 与内核 `linux/socket.h` 冲突 | E091 守卫：在 linux 头文件包含处 `#define sockaddr_storage __linux_sockaddr_storage` 后 `#undef` |
| 2 | `if_pppox.h` 中 `__packed` 重定义 | OHOS 内核头将 `__packed` 当声明符而非宏 | E163 守卫：包含前定义 `__packed` 宏、包含后取消 |
| 3 | pcre2.h / openssl 头文件找不到 | 构建系统只 find_library 未加 include 目录 | CMakeLists 增加 `find_path` + `include_directories` |
| 4 | `-lcrypto`/`-lssl` 链接失败 | 裸库名无法定位 Conan 包路径 | `set(crypto_lib ${CRYPTO_CRYPTO_LIB} ${CRYPTO_LIBRARY})` 用全路径 |
| 5 | `-lucontext` 链接失败 | OHOS musl libc 无 getcontext/setcontext | 依赖 libucontext/1.5.2（独立 PR 发布），`-L<libucontext lib>` |
| 6 | `pthread_cancel` 链接失败 | OHOS musl 不支持线程取消（E127） | triton md.c/timer.c：用 eventfd 唤醒 + 停止标志 + join 替代，`#if defined(__linux__) && !defined(__GLIBC__)` 守卫 |
| 7 | 运行时找不到 `triton/libtriton.so` | NEEDED 含相对路径，musl 按 CWD 解析 | 在二进制目录内运行（或安装后按 INSTALL_RPATH 解析） |

## 源码修改

已修改源码（将固化为 patches/）：
- `accel-pppd/triton/md.c`、`accel-pppd/triton/timer.c`：E127 pthread_cancel 替代
- `accel-pppd/net.c`、`session.c`、`vlan-mon/vlan_mon.c`、`ctrl/l2tp/l2tp.c`、`ctrl/ipoe/*.c`、`ipv6/dhcpv6.c`、`ifcfg.c`、`libnetlink/*.c`、`ppp/*.c`、`cli/show_sessions.c`、`ctrl/pptp/pptp.c` 等：E091 sockaddr_storage 守卫
- `accel-pppd/include/linux_ppp.h`、`include/if_pppox.h`、`include/radius.h`、`ctrl/ipoe/ipoe.h`、`ctrl/pppoe/pppoe.h`、`libnetlink/libnetlink.h`：E091/E163 守卫
- `CMakeLists.txt`：find_path include 目录 + crypto 全路径链接

## 依赖版本

- `openssl/3.5.6.1.1`（已发布 ohpcd）
- `pcre2/10.45.1.1`（已发布 ohpcd）
- `libucontext/1.5.2`（已合入 main 并已发布到 ohpcd；PR #5752）

## 验证结果

```text
构建: 0 错误，accel-pppd + accel-cmd + 24 个共享模块全部链接成功
accel-pppd --version: exit 0，输出 "accel-ppp 1.14.0"
accel-pppd --help: exit 0，完整 usage
accel-cmd --help: exit 0
accel-pppd -c <缺失文件>: exit 1（失败关闭）
accel-pppd -c <最小配置>: 守护进程持续运行（SIGKILL 终止，exit 137）
```

## 注意事项

- 运行时 PPP 会话建立需要内核 `/dev/ppp` 与 PPPIOC ioctls（OHOS 规范 sysroot 已含 linux/ppp-ioctl.h、if_ppp.h 头文件）；smoke 测试仅验证信息选项与守护进程启动，未声明真实 PPP/PPPoE 会话。
- 当前验证设备的 `/dev/ppp` 节点存在，但本进程以非 root 身份打开时返回 `EACCES`；设备没有可用的 PPPoE 对端，且未提供 pppd/拨号工具，因此尚未完成端到端 PPP/PPPoE 连接验证。必须在具备 PPP 权限、实际以太网接入接口和认证对端的 OHOS 设备上复测后，才能宣称主功能可用。
- 上游 tag 1.14.0 实际包含 17 个 pytest 用例；已在当前 OHOS 环境安装 pytest 9.1.1 并实际执行：7 通过、2 失败、1 跳过、7 环境错误（41.2%）。
  - 通过：test_accel_cmd_version、test_accel_cmd_non_existent_host、test_accel_cmd_mcast_host、test_accel_cmd_commands、test_accel_pppd_version、test_load_all_modules、test_pcre_negative_cases。
  - 失败：test_vlan_mon_kernel_module_loaded / test_ipoe_kernel_module_loaded（OHOS 内核无 vlan_mon/ipoe 模块，无法用户态修复）。
  - 环境错误：test_pppoe_discovery / test_pppoe_vlan_mon（无 ip 命令）、test_pppoe_session_*（缺 pppd + 特权网络）、test_ipoe_shared_session_*（缺 dhclient + IPoE 模块 + 特权网络）。
  - 跳过：test_pppoe_pado_delay（无 pppoe-discovery -a/-t）。
- test_load_all_modules / test_pcre_negative_cases 曾因模块 .so 在 OHOS musl 下缺少 libtriton.so / libconnlimit.so / libcrypto.so / libradius.so 的 DT_NEEDED 而启动失败；新增补丁 0027-0032 显式链接后实测通过（全模块加载 0 失败）。
- 上游可运行的用例逻辑已固化为 test_package/smoke_test.py 等效测试（10 个断言全部通过，含全模块配置启动 0 加载失败的内核模块用例用户态等效）。
- 逐用例「无法运行」证据链（报错位置/修复尝试/系统级证明）见 reports/unrunnable-evidence.md。
---

**编译结束**: 2026-08-19 01:43
**最终状态**: published
