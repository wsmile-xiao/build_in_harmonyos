# E430 — OHOS(musl) 无延迟绑定：dlopen 插件在装载时即完成全部重定位

> Draft: E430-draft-74DD（kamailio-memcached 6.0.6 适配产出）

## 错误特征

在一个**不提供宿主符号**的独立进程里装载宿主插件（如 Kamailio 模块 `memcached.so`，
或任何"由宿主提供 API、插件保留未定义符号"的设计）时：

```text
$ dlopen("memcached.so", RTLD_LAZY)
dlerror: Error relocating .../memcached.so: pv_get_null: symbol not found
```

即使用 `RTLD_LAZY` 也一样失败 —— 这与 Linux/glibc 上"RTLD_LAZY 可延迟解析"的直觉相反。

## 触发条件

- 平台: OHOS / HarmonyOS PC（musl libc）
- 阶段: runtime（装载期）
- 对象形态: dlopen 插件，且刻意保留宿主 ABI 未定义符号
  （本例 kamailio 模块的 21 个 core 符号：`_km_log_func`、`dprint_*`、`pv_*`、`MD5StringArray` …）

## 根因分析

musl 的动态装载**不做延迟绑定**：`dlopen()` 返回之前，对象的重定位表已被完整解析。
因此"未定义符号由宿主在第一次调用时再解析"这一 glibc 假设在 OHOS 上不成立。

这不是缺陷，而是 Kamailio 模块装载模型的正确行为：插件**只能**由提供这些符号的
宿主进程装载（`kamailio` 二进制以 `-Wl,-export-dynamic` 导出自身符号）。

## 解决方案

### 推荐方案（验证插件）
在夹具里**模拟宿主**：定义宿主 ABI 桩并以 `-rdynamic`（`--export-dynamic`）导出，
再 `dlopen` 插件。

```c
/* kamailio_host_stubs.c —— 21 个宿主 ABI 桩，仅供重定位，不参与执行 */
int  process_no = 0;
char log_level_info[512] = {0};
int  pv_get_null(void *msg, void *param, void *res) { return 0; }
/* ... */
```
```cmake
target_link_options(test_memcached_module PRIVATE "-rdynamic")
```

同时用 ELF 自检断言"宿主依赖面"是正确的：

```text
未定义符号集合 ⊇ {pv_get_null, _km_log_func, MD5StringArray}
未定义符号集合 ∩ {memcached_*} = ∅        # 静态依赖必须已内嵌
```

### 禁止做法

- ❌ 在无宿主的独立进程里 `dlopen` 宿主插件，然后把 `symbol not found` 当成"包坏了"
- ❌ 用 `dlopen(..., RTLD_NOW)` 的成败差异去判断延迟绑定（musl 下两者行为一致）
- ❌ 为了让裸进程能装载，把宿主 ABI 变成插件自带的弱符号（破坏 Kamailio 模块契约）

## 验证

```bash
# 裸进程：必须失败，且错误指向宿主符号
./dlopen_probe memcached.so         # 期望：Error relocating ...: pv_get_null: symbol not found
# 宿主桩 + -rdynamic：必须成功
./test_memcached_module             # 期望：CHECK-OK: module-dlopen-lazy
```

## 关联条目

- 相关: E429（依赖 .pc 漏声明 system_libs 导致的 C++ 运行时未解析）
- 相关: E431（make /bin/sh 下 pkg-config 探测不稳定）
