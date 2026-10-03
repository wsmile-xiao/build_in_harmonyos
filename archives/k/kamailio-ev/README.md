# kamailio-ev

Kamailio SIP 服务器的 `ev` 子包模块（`evapi.so`）——基于 **libev** 的网络事件广播
（Network event broadcast API）：把 SIP 事件推送给外部 TCP 客户端，也接收客户端
消息并在 kamailio 配置/KEMI 脚本中回放（`evapi_relay*`、`evapi_unicast*`、
`evapi_multicast*`、`evapi_close`、`evapi_set_tag`）。由 kamailio 运行时
`loadmodule` 加载。

- 上游项目：<https://www.kamailio.org> / <https://github.com/kamailio/kamailio>
- 适配版本：6.0.6
- 子包对应关系：Alpine `main/kamailio` APKBUILD 的 `kamailio-ev` 子包
  （`_mod_list_ev="evapi"`，"Network event broadcast API"）
- 许可：GPL-2.0-or-later

## 产物

| 路径（包内） | 内容 |
|---|---|
| `lib/kamailio/modules/evapi.so` | 模块动态库（供 kamailio `loadmodule "evapi.so"`） |
| `licenses/COPYING` | 上游许可证 |

不依赖 kamailio 本体包：模块 `.so` 的核心符号由 kamailio 主程序在加载时提供。

## 平台适配（HarmonyOS PC / aarch64）

采用与同族 `kamailio-tls`、`kamailio-gcrypt`、`kamailio-xml`、`kamailio-extras`
一致的 **零补丁** 路线：

1. **平台探测宏**：`OS=harmonyos` 不在上游 `Makefile.defs` 的 linux/solaris/freebsd/darwin
   分支内，平台探测宏全部缺失（core 头会直接 `#error`）；经 `make` 命令行
   `extra_defs` 注入 linux 分支等价宏集（9 项，对照 OHOS SDK musl sysroot 实证）。
2. **只编模块、不编 core**：`core/resolve.c` 的 `_res`（`HAVE_RESOLV_RES`）与
   `core/lock_ops.h` 的 `union semun`（`HAVE_UNION_SEMUN`）在 OHOS musl 头文件中无对应
   定义，仅编译主程序时才触发 → 本配方只编模块，不触碰这两条路径。
3. **libev 依赖探测钉死**：`evapi/Makefile` 在 `CROSS_COMPILE` 为空时用
   `pkg-config --exists libev` 探测（注意变量名是**裸 `BUILDER`**，与 tls 的
   `SSL_BUILDER`、gcrypt 的 `GCRYPT_BUILDER` 不同），探测失败才回退
   `-I$(LOCALBASE)/include` + `-L$(LOCALBASE)/lib -lev`。conan 制品仓的 `libev/4.33`
   **不携带 `.pc` 文件**，故配方显式传 `BUILDER=` 跳过探测分支、确定性走 LOCALBASE
   回退，并把 `LOCALBASE`/`CPATH`/`LIBRARY_PATH` 全部指向 conan libev 包目录——避免
   构建机上同名系统库劫持探测结果（实测见 `6.0.6/notes.md`）。

## 构建

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

- 依赖：`libev/4.33`（已在制品仓发布预编译包，`conan download` 实测可消费）。
- `-j1`：E525/E074 —— OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO
  传递令牌，`-j>1` 存在挂起/报错风险（与同族 10+ 个 `kamailio-*` 配方一致）。

## 测试

| 层级 | 内容 | 结果 |
|---|---|---|
| 上游测试 | `utils/kamctl/dbtextdb/dbtextdb_test.py`（源码包内唯一自包含上游 unittest） | 3/3 通过（`build()` 内真实执行） |
| 产物检查 | `test_package/check_evapi_module.py`（ELF/契约名/DT_NEEDED/符号闭包，纯 Python） | 17/17 |
| 鸿蒙端到端 | `test_package/test_evapi_e2e.c`（dlopen 加载路径 + core 桩层 + 真实 libev 回调） | 134/134 |

上游 `evapi` 模块自身无自动化测试套件（源码包 test/tests 全量 17 个文件，无一涉及
evapi），逐项清点与未执行原因见 `6.0.6/test_package/MANIFEST.yml`。

## 版本索引

| 版本 | 状态 | Conan 引用 |
|---|---|---|
| 6.0.6 | built | `kamailio-ev/6.0.6` |
