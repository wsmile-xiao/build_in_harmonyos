# kamailio-ims

Kamailio SIP 服务器的 IMS（IP Multimedia Subsystem，IP 多媒体子系统）模块集
（16 个模块 `.so`），由 kamailio 运行时 `loadmodule` 加载。

- 上游项目：<https://www.kamailio.org> / <https://github.com/kamailio/kamailio>
- 适配版本：6.0.6
- 子包对应关系：Alpine `main/kamailio` APKBUILD 的 `kamailio-ims` 子包
  （`_mod_list_ims` 16 项："IP Multimedia Subsystem (IMS) support"）
- 许可：GPL-2.0-or-later

## 产物

| 路径（包内） | 内容 |
|---|---|
| `lib/kamailio/modules/cdp.so` | Diameter 协议栈（CCDX）模块 |
| `lib/kamailio/modules/cdp_avp.so` | Diameter AVP 定义（cdp 的伴随模块） |
| `lib/kamailio/modules/ims_*.so` | IMS 业务模块 14 个（ims_auth / ims_charging / ims_dialog / ims_diameter_server / ims_icscf / ims_ipsec_pcscf / ims_isc / ims_ocs / ims_qos / ims_qos_npn / ims_registrar_pcscf / ims_registrar_scscf / ims_usrloc_pcscf / ims_usrloc_scscf），合计 16 个 `.so` |
| `licenses/COPYING` | 上游许可证 |

不依赖 kamailio 本体包：模块 `.so` 的核心符号由 kamailio 主程序在加载时提供。

## 平台适配（HarmonyOS PC / aarch64）

采用与同族 `kamailio-tls`、`kamailio-xml`、`kamailio-extras`、`kamailio-gcrypt`
一致的 **零补丁** 路线：

1. **平台探测宏**：`OS=harmonyos` 不在上游 `Makefile.defs` 的 linux/solaris/freebsd/darwin
   分支内，平台探测宏全部缺失（core 头会直接 `#error`）；经 `make` 命令行
   `extra_defs` 注入 linux 分支等价宏集（9 项，对照 OHOS SDK musl sysroot 实证）。
2. **只编模块、不编 core**：`core/resolve.c` 的 `_res`（`HAVE_RESOLV_RES`）与
   `core/lock_ops.h` 的 `union semun`（`HAVE_UNION_SEMUN`）在 OHOS musl 头文件中无对应
   定义，仅编译主程序时才触发 → 本配方只编模块，不触碰这两条路径。
3. **三个外部库探测钉死**（构建机系统库无从劫持）：
   - **libxml2**（6 个模块）：模块 Makefile 的探测链是 `which xml2-config` →
     `pkg-config --exists libxml-2.0` → `LOCALBASE` 回退。配方以命令行变量
     `XML2CFG=`（空值）覆盖 Makefile 内部赋值，强制走 `LOCALBASE` 回退分支，
     `LOCALBASE` 指向 conan libxml2 包目录。
   - **libmnl**（`ims_ipsec_pcscf`）：探测链是 `which pkg-config` + `--exists libmnl`。
     配方以命令行变量 `BUILDER=`（空值）钉死 `-lmnl` 回退分支，库搜索路径由
     `LIBRARY_PATH` 提供。
   - **openssl**（`cdp`）：`cdp/Makefile` 的 `ifneq ($(OS),darwin)` 分支**无条件**
     追加 `-lssl -lcrypto`（与 xml2 探测无关，`OS=harmonyos` 恒真），故必须显式声明
     openssl 依赖。

## 构建

```bash
conan create . -pr:h ohos-aarch64 -pr:b default --build=missing
```

- 依赖：`libxml2/2.15.3.1`、`libmnl/1.0.5`、`openssl/3.5.8.1`，均已在制品仓发布预编译包。
- `-j1`：E525/E074 —— OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO
  传递令牌，`-j>1` 存在挂起/报错风险（与同族 11 个 `kamailio-*` 配方一致）。
- 三个外部库在 OHOS sysroot/目标机均无同名库（sysroot 实证无 `libxml2.so`/`libmnl.so`/
  `libssl.so`/`libcrypto.so`），故按仓库口径（R26）不视为系统同名库。实测形态：
  **libxml2 为运行时动态依赖**（`DT_NEEDED: libxml2.so.16`，部署时经 `LD_LIBRARY_PATH`
  定位）；**libmnl（`ims_ipsec_pcscf`）与 openssl（`cdp`）的 conan 包只有静态形态**，
  已静态内嵌进模块、无运行时 `.so` 需求（详见 `6.0.6/notes.md` §4.4）。

## 版本索引

| 版本 | 状态 | Conan 引用 |
|---|---|---|
| 6.0.6 | built | `kamailio-ims/6.0.6` |
