# kamailio-xmpp

kamailio 的 **xmpp 模块**（`xmpp.so`）—— SIP↔XMPP 网关（component / server 两种工作形态），
XMPP stanza 解析由模块内嵌的 xode 解析器经 **expat** 完成；由 kamailio 运行时
`loadmodule`（dlopen）加载。

- 上游项目：<https://www.kamailio.org> / <https://github.com/kamailio/kamailio>
- 适配版本：6.0.6
- 对应上游路径：`src/modules/xmpp`（上游 `modules.lst` 中模块名 `xmpp`）
- 许可：GPL-2.0-or-later

## 产物

| 路径（包内） | 内容 |
|---|---|
| `lib/kamailio/modules/xmpp.so` | XMPP 网关模块（`loadmodule "xmpp.so"` 加载） |
| `share/kamailio/doc/xmpp/README` | 模块文档（modparam 与路由函数说明） |
| `licenses/COPYING` | 上游许可证 |

不依赖 kamailio 本体包：模块 `.so` 的核心符号（`cfg_*`、`shm`、`find_export` 等）由 kamailio
主程序在加载时提供。运行期需先加载 `tm` 模块（模块 `mod_init()` 中调用 `load_tm_api()`）。

独立依赖：**expat**（`DT_NEEDED` 含 `libexpat.so`）。OHOS sysroot 无 libexpat ⇒ 非"系统同名库"，
按 R26 口径由 Conan 依赖链提供运行时 `.so`（消费者 `conan install` 自动拉取；手工部署需把
expat 包 `lib/` 加入 `LD_LIBRARY_PATH`，musl 无 rpath）。

## 平台适配（HarmonyOS PC / aarch64）

| 项 | 做法 |
|---|---|
| 平台分支 | kamailio 以 `uname -s` 判定 OS，OHOS 上是 `HarmonyOS`，不落入 `Makefile.defs` 任何分支 → 显式 `OS=linux`（OHOS 无 harmonyos 专属分支），等价 linux 分支宏集 |
| 模块↔core 口径一致 | `core/sr_module.c` 对 `SER_FULL_VERSION`（`kamailio 6.0.6 (aarch64/linux)`）与 `SER_COMPILE_FLAGS` 做**严格 strcmp**；配方用 `SCTP=0`（sysroot 无 `netinet/sctp.h`）+ `DEFS_RM=-DHAVE_RESOLV_RES`（OHOS libc 无 `_res`）与 core 完全对齐。实测已用完整 core 装载本模块（无 version/flags mismatch） |
| expat 探测钉死 | 模块 Makefile 的 `-I$(LOCALBASE)/include` / `-L$(LOCALBASE)/lib -lexpat` 经 `LOCALBASE` 指向 Conan expat 包目录，构建机系统 expat 无法介入 |
| 并行度 | `-j1`（OHOS SELinux 禁止用户进程创建 FIFO，GNU make jobserver 依赖 FIFO 传令牌） |
| 补丁 | **1 个上游缺陷修复**：`xode_from.c` 的 `_xode_put_expatattribs()` 缺少 `atts[i]` 判空 → 任何无属性元素解析即 SIGSEGV（详见版本目录 notes.md）。补丁与平台无关，不含平台宏 |

## 验证

- `conan create` rc=0；`test_package` 31 项断言全 PASS（19 项产物/平台契约 + 12 项消费者实测，含鸿蒙专项）
- 上游 `test/unit` **49/49 全量执行**（OK=5 / FAIL=9 / SKIP=35 / TIMEOUT=0），9 项 FAIL 根因逐个取证，均非本包产物缺陷
- 消费者用例真实调用模块 XMPP 解析 API（`xode_from_str` → expat 运行路径 → `xode_get_name`/`xode_get_attrib`/`xode_get_tagdata`/`xode_to_str`）

细节见 `6.0.6/notes.md`。
