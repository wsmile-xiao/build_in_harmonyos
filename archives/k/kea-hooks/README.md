# kea-hooks

ISC Kea 的 **hooks（callout）框架库**，适配 HarmonyOS PC（OHOS aarch64）。

## 是什么

`libkea-hooks` 是 Kea 的钩子（hook / callout）框架本身：kea-dhcp4、kea-dhcp6 以及所有
用户 hook 库（perfmon、limits、lease-query 等）都链接它或经它被加载。它提供：

- `ServerHooks` —— hook 点注册表（`context_create` / `context_destroy` + 业务 hook 名）；
- `CalloutHandle` / `CalloutManager` —— 按库、按 hook 注册与调用 callout，报文级
  参数（argument）与 per-library context 的传递，`next_step` 状态（continue/skip/drop/park）；
- `LibraryManager` / `LibraryManagerCollection` —— 运行时 `dlopen()` 用户库、校验
  `version()`/`load()`/`unload()`/`multi_threading_compatible()` 契约；
- `HookLibInfo` / `extractNames` —— `hooks-libraries` 配置项的数据模型。

- 上游项目：ISC Kea 3.0.3（MPL-2.0）
- 源码路径：`src/lib/hooks/`（与 Kea 同一源码树，Meson 单工程构建）
- 产物：`lib/libkea-hooks.so.121.0.0`（SONAME `libkea-hooks.so.121`）+ `include/kea/hooks/*.h`

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| boost | 1.85.0 | 强制；1.90/1.91 制品仓包缺 Kea 实际使用的头文件，须固定版本 |
| log4cplus | 2.2.0.1 | 强制；Kea 日志后端（`libkea-log` 依赖它） |
| openssl | 3.5.8.1 | 强制；默认 crypto 后端（`CRYPTO_DEP`） |
| gtest | 1.17.0.1 | 测试期（`-Dtests=enabled`） |
| meson | 1.11.0 | 构建工具（tool_requires，须 ≥ 1.10） |

包内同时携带 `libkea-hooks.so` 的完整加载闭包（`readelf -d` 递归实测 7 个 Kea 共享库：cc、asiolink、
log、log-interprocess、util、exceptions、cryptolink；其中 `libkea-hooks.so` 直接 DT_NEEDED 为
cc/log/util/exceptions 4 个）及它们的公共头，因此安装后无需额外的 Kea 运行库即可直接链接与加载。

## OHOS 适配要点

1. **平台名归一化**：Meson 报告 `harmonyos`，Kea 用 `build_machine.system()`
   做平台分支且白名单不含它 → 顶层 `meson.build` 归一化为 `linux`。
2. **boost/musl 差异**：musl `pthread.h` 无 `pthread_setcancelstate` 声明 →
   定义 boost 官方逃生宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE`。
3. **Meson 工具链**：需同时使用 `PkgConfigDeps`（依赖 `.pc`）与
   `MesonToolchain`；配置期 `cpp.run()` 探针要求 host 共享依赖在
   `LD_LIBRARY_PATH` 可见；`llvm-ar`/`llvm-ranlib` 从编译器路径推导为绝对路径。
4. **构建范围**：Kea 3.0 是单 Meson 工程（1432 个 ninja 边），本包只编译
   `kea-hooks` + 上游测试目标 + 10 个测试夹具库（182 个边），不构建 dhcp4/dhcp6
   服务器等无关目标。

## 上游测试

Meson 注册的 gtest 套件 `kea-hooks-tests` 在 `build()` 内真实执行：

| 套件 | 用例 | 说明 |
|------|------|------|
| `kea-hooks-tests` | 121 | callout handle / callout manager / callout handle associate / parking lots / server hooks / library manager / library manager collection / handles（源码宏 122，含 1 个 `DISABLED_` 被 gtest 排除） |

本版本实测：121/121 通过，0 失败，0 跳过。

`test_package/` 另有消费者视角测试：`test_kea_hooks`（链接 libkea-hooks 调公共 API）与
**鸿蒙特有**的 `test_ohos_platform`（校验产物 ELFCLASS64/EM_AARCH64、DT_NEEDED 为 OHOS musl
`libc.so` / `libc++_shared.so` 而非 glibc 命名、`dlopen(RTLD_NOW)` 可解析，以及 package 导出的
OHOS 专用宏 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 确实进入消费者编译行）。

## 使用

```bash
conan install --requires=kea-hooks/3.0.3 -pr:h=<ohos-aarch64 profile>
```

消费者（例如 Kea 服务器或用户 hook 库）：

```cpp
#include <hooks/hooks.h>          // KEA_HOOKS_VERSION
#include <hooks/server_hooks.h>   // isc::hooks::ServerHooks

isc::hooks::ServerHooks& hooks = isc::hooks::ServerHooks::getServerHooks();
int index = hooks.registerHook("my_hook_point");
```
