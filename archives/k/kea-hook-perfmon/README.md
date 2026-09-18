# kea-hook-perfmon

ISC Kea 的 **perfmon**（performance monitoring）hook 插件，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`libdhcp_perfmon.so` 是 Kea DHCP 服务器的性能监控钩子：按报文事件（`pkt4_receive`/
`pkt4_send`/`pkt6_receive`/`pkt6_send` 等）统计处理时长，支持 monitored durations
与 alarm（低/高水位）配置，并通过控制通道命令（`perfmon-control`、
`perfmon-get-all-durations`）向外暴露统计。插件由 Kea 服务器在运行时 `dlopen()`
加载（`hooks-libraries` 配置项），不是被链接的库。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/hooks/dhcp/perfmon/`（与 Kea 同一源码树，Meson 单工程构建）
- 安装路径：`lib/kea/hooks/libdhcp_perfmon.so`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件，须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端 |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（`CRYPTO_DEP`） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带插件运行时加载的 20 个 Kea 共享库（`readelf -d` NEEDED 闭包），
因此安装后无需额外的 Kea 运行库即可被服务器加载。

## OHOS 适配要点

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
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径。

## 上游测试

两个 Meson 注册的 gtest 套件在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `dhcp-perfmon-lib-tests` | 125 | hook 单元测试（源码宏 126，含 1 个 `DISABLED_speed` 被 gtest 排除） |
| `dhcp-perfmon-libload-tests` | 5 | 插件的加载/卸载契约 |

本版本实测：130/130 通过，0 失败，0 跳过。

### 包内测试（test_package）

| 用例 | 类型 | 说明 |
|------|------|------|
| `test_perfmon_hook` | 消费者契约 | `dlopen` 加载包内 hook，校验 `version`/`load`/`unload` 契约符号、`perfmon_control`/`perfmon_get_all_durations` 控制入口与 hook ABI 版本 30003 |
| `test_ohos_platform` | **鸿蒙特有** | 校验产物平台 ABI 签名：ELFCLASS64 / `EM_AARCH64`（OHOS PC aarch64）、`DT_NEEDED` 为 musl `libc.so` 且非 glibc `libc.so.6`、链接 `libc++_shared.so`，并验证 OHOS 加载器 `dlopen(RTLD_NOW)` 可解析插件 |

本版本实测：2/2 通过（含鸿蒙特有测试 1 项）。

## 使用

```bash
conan install --requires=kea-hook-perfmon/3.0.3 -pr:h=<ohos-aarch64 profile>
```

Kea 服务器加载（`kea-dhcp4.conf`）：

```json
{
  "Dhcp4": {
    "hooks-libraries": [
      { "library": "<prefix>/lib/kea/hooks/libdhcp_perfmon.so" }
    ]
  }
}
```
