# kamailio-gcrypt

Kamailio SIP 服务器的 `gcrypt` 模块（`gcrypt.so`）——基于 libgcrypt 的密码学函数
（AES-128 加解密、UUID 生成/校验等），由 kamailio 运行时 `loadmodule` 加载。

- 上游项目：<https://www.kamailio.org> / <https://github.com/kamailio/kamailio>
- 适配版本：6.0.6
- 子包对应关系：Alpine `main/kamailio` APKBUILD 的 `kamailio-gcrypt` 子包
  （`_mod_list_gcrypt="gcrypt"`，"Cryptography functions using libcrypt"）
- 许可：GPL-2.0-or-later

## 产物

| 路径（包内） | 内容 |
|---|---|
| `lib/kamailio/modules/gcrypt.so` | 模块动态库（供 kamailio `loadmodule "gcrypt.so"`） |
| `licenses/COPYING` | 上游许可证 |

不依赖 kamailio 本体包：模块 `.so` 的核心符号由 kamailio 主程序在加载时提供。

## 平台适配（HarmonyOS PC / aarch64）

采用与同族 `kamailio-tls`、`kamailio-xml`、`kamailio-extras` 一致的 **零补丁** 路线：

1. **平台探测宏**：`OS=harmonyos` 不在上游 `Makefile.defs` 的 linux/solaris/freebsd/darwin
   分支内，平台探测宏全部缺失（core 头会直接 `#error`）；经 `make` 命令行
   `extra_defs` 注入 linux 分支等价宏集（9 项，对照 OHOS SDK musl sysroot 实证）。
2. **只编模块、不编 core**：`core/resolve.c` 的 `_res`（`HAVE_RESOLV_RES`）与
   `core/lock_ops.h` 的 `union semun`（`HAVE_UNION_SEMUN`）在 OHOS musl 头文件中无对应
   定义，仅编译主程序时才触发 → 本配方只编模块，不触碰这两条路径。
3. **libgcrypt 依赖探测钉死**：`gcrypt/Makefile` 在 `CROSS_COMPILE` 为空时用
   `pkg-config --exists libgcrypt` 探测，未命中回退 `LOCALBASE`。配方以三重手段钉死到
   conan 依赖包：命令行变量 `GCRYPT_BUILDER="pkg-config libgcrypt"` + `PKG_CONFIG_PATH`
   指向依赖包；`CPATH`/`LIBRARY_PATH` 兜底；`LOCALBASE` 指向 libgcrypt 包目录。

## 构建

```bash
conan create . -pr:h ohos-aarch64 -pr:b default --build=missing
```

- 依赖：`libgcrypt/1.12.2`（+ 传递依赖 `libgpg-error/1.55`），均已在制品仓发布预编译包。
- `-j1`：E525/E074 —— OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO
  传递令牌，`-j>1` 存在挂起/报错风险（与同族 10 个 `kamailio-*` 配方一致）。

## 版本索引

| 版本 | 状态 | Conan 引用 |
|---|---|---|
| 6.0.6 | built | `kamailio-gcrypt/6.0.6` |
