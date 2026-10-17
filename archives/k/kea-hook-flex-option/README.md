# kea-hook-flex-option

ISC Kea 的 **flex-option**（表达式计算选项值）hook 插件，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`libdhcp_flex_option.so` 是 Kea DHCPv4/DHCPv6 服务器的选项计算钩子：把选项值从
静态配置改为**表达式求值**——在分配租约时按 `evaluate-expression` 配置计算选项
内容（可引用请求的字段、客户端类、租约状态等），并支持 sub-option 的嵌套定义
与值替换。插件由 Kea 服务器在运行时 `dlopen()` 加载（`hooks-libraries` 配置项），
不是被链接的库。与家族配方 kea-hook-ping-check（仅 kea-dhcp4、需要原始套接字）
不同，flex-option 同时服务 v4/v6 双协议且为**纯逻辑插件**：无 SOCK_RAW、无特权
依赖、无外部数据文件。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/hooks/dhcp/flex_option/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：`lib/kea/hooks/libdhcp_flex_option.so`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件（`interprocess`/`circular_buffer`），须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端 |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带插件运行时加载的 20 个 Kea 共享库（`readelf -d` NEEDED 闭包），
因此安装后无需额外的 Kea 运行库即可被服务器加载。

## OHOS 适配要点

本配方与家族配方 kea-hook-limits/kea-hook-ping-check 同属 Kea 3.0.3 单源码树，
4 个补丁**整组逐字节复用**（0001/0002 与 limits 一致；0003/0004 与 ping-check
一致），适配要点逐项保留：

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`，使
   `iface_mgr_linux.cc` / `pkt_filter_lpf.cc` 等 Linux 后端源码被选中。
2. **UAPI 头冲突**：OHOS 的 `linux/socket.h` 与 musl `sys/socket.h` 都定义
   `struct sockaddr_storage` → 包含 netlink 头时用 define-guard 重命名内核侧
   定义（`__linux__ && !__GLIBC__` 守卫，无需平台宏）。
3. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
4. **Meson 工具链**：需同时使用 `PkgConfigDeps`（依赖 `.pc`）与
   `MesonToolchain`；配置期 `cpp.run()` 探针要求 host 共享依赖在
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径
   （OHOS 的 Python subprocess 不解析 PATH）。
5. **脚本执行一律经解释器**：OHOS 内核拒绝 shebang 脚本的 execve（无论执行位），
   而 Kea 的 configure 期会直接执行 `scripts/env.sh`、`scripts/grabber.py`、
   `config-report.sh`、`tools/mk_cfgrpt.sh` 等辅助脚本。补丁将脚本变量重定义为
   解释器前缀数组（`['/bin/sh', 脚本]` / `[find_program('python3').full_path(),
   脚本]`）；配方自身的 `build()` 也遵循同一纪律——conan 的 meson 包
   `bin/meson` 是 shell 包装脚本，改经 `sh "<meson 包>/bin/meson"` 调用。
6. **soname 物化**：OHOS /storage 沙箱拒绝符号链接，meson 的版本化 soname
   只以符号链接发布 → `build()` 在 compile 后以复制方式物化 soname 名
   （`_materialize_sonames`，幂等）。
7. **并发限制**：OHOS app 沙箱限制并发进程，`meson compile -j 8` 防
   posix_spawn EAGAIN（家族配方 host-cmds 实测）。

## 上游测试

两个 Meson 注册的 gtest 套件在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `dhcp-flex-option-lib-tests` | 148 | hook 单元测试（flex_option_unittests 63：选项配置解析 / 表达式求值 / 表达式缓存；sub_option_unittests 85：sub-option 定义与值替换） |
| `dhcp-flex-option-libload-tests` | 5 | 插件的加载/卸载契约与回调行为 |

153 例全部为纯逻辑用例：无 root 用例（与 ping-check 的 48 个 Root 组用例不同）、
无外部数据文件，OHOS 沙箱下零 root 零 SKIP 全实跑（实测见版本级 `notes.md`）。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| `test_flex_option_hook` | 消费者契约 | `dlopen` 加载包内 hook，校验 `version`/`load`/`unload` 契约符号与 hook ABI 版本 30003 |
| `test_ohos_platform` | **鸿蒙特有 #1** | 校验产物平台 ABI 签名：ELFCLASS64 / `EM_AARCH64`（OHOS PC aarch64）、`DT_NEEDED` 为 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so`，并验证 OHOS 加载器 `dlopen(RTLD_NOW)` 可解析插件 |
| `test_ohos_runtime` | **鸿蒙特有 #2** | 在 OHOS 加载器下逐个 `dlopen(RTLD_NOW)` 包内 20 个 Kea 运行时库，校验完整 NEEDED 闭包可解析、闭包驻留后 hook 仍可加载且契约符号可解析 |

本版本实测：见版本级 `notes.md`。

## 使用

```bash
conan install --requires=kea-hook-flex-option/3.0.3 -pr:h=<ohos-aarch64 profile>
```

Kea 服务器加载（`kea-dhcp4.conf` / `kea-dhcp6.conf`）：

```json
{
  "Dhcp4": {
    "hooks-libraries": [
      { "library": "<prefix>/lib/kea/hooks/libdhcp_flex_option.so" }
    ]
  }
}
```
