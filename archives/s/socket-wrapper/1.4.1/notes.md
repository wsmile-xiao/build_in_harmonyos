# socket-wrapper 1.4.1 HarmonyOS 适配笔记

## 编译环境

- 目标系统：HarmonyOS 6.0 / OHOS 6.0
- 目标架构：aarch64（CI），x86_64（本地模拟器验证）
- 构建系统：CMake + Ninja
- 编译器：OpenHarmony SDK 26.0.0 Clang 15.0.4
- 兼容 API：20
- 包管理器：Conan 2.29.1
- 状态：built

## 编译步骤

配方从 Samba cwrap 官方发布地址获取 1.4.1 源码并校验 SHA-256，应用版本级补丁后通过 OpenHarmony CMake toolchain 构建共享库。`with_upstream_tests=True` 时以 `cmocka/2.0.2` 作为 `test_requires` 构建上游测试；安装后对 ELF 共享库移除旧 `.codesign` 节并使用 SDK 的 binary-sign-tool 自签名。

本地 x86_64 验证使用 HarmonyOS 6.0 host profile、SDK 自带的 CMake/Ninja/Clang，以及 SDK 26 的 x86_64 sysroot。Conan 的交叉构建宿主是 Windows，因此 `can_run()` 会跳过目标程序执行；目标机执行需在 HarmonyOS 原生 CI 或允许 AF_UNIX 文件 socket 的应用/调试域中完成。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `recvmmsg`/`sendmmsg` 类型冲突 | HarmonyOS musl 的 flags 参数为 `unsigned int`，与 1.4.1 已知分支不匹配 | 增加原型能力探测和对应 typedef、libc wrapper、内部 wrapper、导出函数分支 |
| 2 | `fopen64`、`open64`、`openat64` 重定义 | HarmonyOS musl 将 LFS64 接口定义为普通接口的宏别名 | 在相应拦截函数定义前局部 `#undef` 宏别名 |
| 3 | 链接阶段尝试 `-lsocket -lnsl` | 交叉 `try_compile` 不能可靠运行，产生假阳性 | OHOS 配方显式钉住经 SDK 头文件验证的 musl 能力集 |
| 4 | cmocka 2.x 测试目标缺少头文件或私有符号 | 1.4.1 未完整支持 CMake CONFIG imported target，且 cmocka 2.x 移除了 `_assert_in_range` | 传播 `cmocka::cmocka` 目标，并根据 cmocka 主版本选择 `_assert_uint_in_range` |
| 5 | 上游测试固定使用 `/tmp` | HarmonyOS 环境可能将 `/tmp` 挂载为只读 | 三处测试目录创建逻辑优先使用 `TMPDIR`，保留 `/tmp` 作为回退 |
| 6 | 交叉构建的回显测试在目标机寻找 Windows 绝对路径 | `BINARYDIR` 在编译时展开为宿主构建目录并固化进测试 ELF | `torture.c` 支持 `SOCKET_WRAPPER_ECHO_SERVER` 覆盖；未设置时保持原生 CI 的旧行为 |
| 7 | 模拟器中 wrapper 的 AF_UNIX `bind()` 返回 `EACCES` | HDC `shell` 的 SELinux 域允许普通文件但禁止在 `/data/local/tmp` 创建文件型 Unix socket；最小无 LD_PRELOAD 探针复现；公开镜像因 `undebuggable version` 拒绝 `hdc smode` | 不修改库语义规避系统策略；最终目标机证据需来自允许 AF_UNIX 的应用沙箱、原生 CI 或可调试镜像 |
| 8 | 原生 CI #40332 的 `test_ioctl` 失败 | HarmonyOS 内核对普通、未拦截的 UDP socket 执行 `ioctl(SIOCGPGRP)` 也返回 `EACCES`；其余 30 个上游测试组全部通过 | 仅在检测到 `__OHOS__` 时从 CTest 注册列表移除该平台不支持的测试，其他平台继续执行 |

仓库知识引擎对这些短错误文本给出了不相关的通用匹配，因此最终根因以编译器完整诊断、SDK 头文件和最小目标机探针为准。

## 源码修改

- `0001-ConfigureChecks.cmake.patch`：探测 musl/OHOS mmsg 原型。
- `0002-config.h.cmake.patch`：声明新增能力宏。
- `0003-src-socket_wrapper.c.patch`：适配 mmsg 签名并消除 LFS64 宏别名冲突。
- `0004-tests-CMakeLists.txt.patch`：将 fake UID preload helper 链接到 cmocka CONFIG imported target。
- `0005-tests-test_echo_tcp_get_peer_sock_name.c.patch`：适配 cmocka 2.x 范围断言。
- `0006-tests-test_fcntl_lock.c.patch`：测试目录遵循 `TMPDIR`。
- `0007-tests-test_ioctl.c.patch`：测试目录遵循 `TMPDIR`。
- `0008-tests-torture.c.patch`：共享测试运行目录遵循 `TMPDIR`，并允许目标机覆盖回显服务路径。
- `0009-tests-CMakeLists-ohos-ioctl.patch`：仅在 OHOS 下不注册内核拒绝 `SIOCGPGRP` 的 `test_ioctl`。

补丁 0001 至 0008 由 `scripts/ohc-run.py refresh-patch --auto` 从 pristine/work 源码树生成。补丁 0009 依据 CI #40332 和 1.5.2 的独立探针证据增加，补丁栈通过 `git apply --check` 验证。

## 依赖版本

- 运行时依赖：无
- 测试依赖：`cmocka/2.0.2`

## 当前验证结果

- x86_64 OHOS 主库与 noop 库：编译、安装、自签名通过。
- 启用上游测试：76 个 Ninja 编译/链接步骤通过；Conan 命令退出 0。
- Conan `test_package`：x86_64 配置、编译、链接通过；交叉宿主按 `can_run()` 跳过执行。
- HarmonyOS 6.0.0.48 x86_64 模拟器：全部 31 个已签名上游测试组均在普通 HDC shell 域尝试执行，10 组通过、20 组失败、1 组超时；依赖 AF_UNIX bind 的路径受 SELinux 限制，故该计数不是最终兼容率。
- 回显服务路径 RED/GREEN：无效覆盖稳定出现 `not found`；设置 `SOCKET_WRAPPER_ECHO_SERVER=./echo_srv` 后目标端 helper 成功启动并进入后续 AF_UNIX 初始化，不再引用 Windows 路径。
- Conan 消费者目标的正反向控制通过：不设 `LD_PRELOAD` 时被测试程序拒绝，恢复预加载后越过 wrapper 检查并在重定向后的 AF_UNIX `bind()` 处被普通 `shell` 域以 `EACCES` 拒绝。
- 经用户明确授权尝试 `hdc smode`，模拟器返回 `Cannot set root run mode in undebuggable version`，权限未发生变化。
- HarmonyOS 原生 CI #40332：构建、链接和签名全部成功，31 个上游测试组中 30 个通过；唯一失败为 `test_ioctl` 的 `SIOCGPGRP` 断言。0009 补丁将 OHOS 适用测试集收敛为 30 项，等待 CI 复跑确认。
- 最终兼容计数和平台限制分类将在具备允许 AF_UNIX socket 的运行域后补充。

## 注意事项

- 当前归档状态为 `built`：交叉构建、Conan 打包及消费者链接均已通过。
- 普通 HDC shell 域的目标机结果受 SELinux 限制，公开模拟器镜像也不可切换 root；在允许 AF_UNIX bind 的运行域完成复测前，不声明最终兼容通过率。
- socket-wrapper 依赖 `LD_PRELOAD`，仅提供共享库；`shared=False` 会被配方拒绝。
- `SOCKET_WRAPPER_DIR` 必须是短路径、可写，并允许创建 AF_UNIX socket inode。
- `binary-sign-tool` 在 SDK 中以 JAR 提供时，可通过包装命令传给 `OHOS_BINARY_SIGN_TOOL`；缺失签名工具时配方会明确失败，不静默发布未签名 ELF。

---

**编译结束**: 2026-09-04
**最终状态**: built（可调试镜像或应用域复测待完成）
