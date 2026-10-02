# DRAFT-11941: kamailio 模块集交叉编译——按模块 Makefile 探测链钉死外部库

- 条目主题：以 **kamailio** 为代表的"一个配方打包多个插件模块、且模块各自探测不同外部库"的构建体系，在 OHOS 交叉编译下外部库探测被宿主工具链劫持（或半途回退）导致头/库路径分裂的共性问题与处理策略。
- 状态：草稿（待知识库主编审核，拟提升编号 Exxx）
- 关联 PR：#13949（feat/kamailio-ims-6.0.6，16 个 IMS 模块）
- 关联先例：kamailio-xml（libxml2）、kamailio-gcrypt（libgcrypt）、kamailio-unixodbc（unixODBC）

## 适用场景

kamailio 的模块 Makefile（`src/modules/*/Makefile`）通过 shell 探测决定外部库的 `-I/-L/-l`：

```makefile
# xml2 系 6 个模块（cdp / ims_auth / ims_icscf / ims_isc / ims_registrar_pcscf / ims_registrar_scscf）
XML2CFG ?= $(shell which xml2-config)
DEFS += $(shell $(XML2CFG) --cflags ...)     # 命中宿主 xml2-config 即被劫持
# libmnl 模块（ims_ipsec_pcscf）
ifeq ($(shell which pkg-config),)
  DEFS += -I$(LOCALBASE)/include ...
else ifeq ($(shell pkg-config --exists libmnl && echo yes),yes)
  ...
endif
# cdp 额外分支：与 xml2 探测无关，OS 非 darwin 即追加
ifneq ($(OS),darwin)
  LIBS += -lrt -lpthread -lssl -lcrypto
endif
```

交叉编译到 OHOS aarch64 时的两类故障面：

1. **宿主探测劫持**：构建机 PATH 上存在 `xml2-config`/`pkg-config` 且其 `.pc` 指向宿主（x86_64/glibc）路径 → 编进宿主的 `-I/-L`，链接期在 OHOS sysroot/conan 前缀里找不到同名库（`cannot find -lxml2` / ABI 混链）。
2. **半途回退**：探测失败时 Makefile 回退到 `LOCALBASE`，但只传 `LOCALBASE=...` **不生效**——`XML2CFG`/`BUILDER` 已被 `?=`/`$(shell …)` 赋值，必须**用命令行变量覆盖为空值**才能强制走回退分支。
3. **无条件链接分支**：`ifneq ($(OS),darwin)` 在 `OS=harmonyos` 下恒真 → cdp 无条件追加 `-lssl -lcrypto`，即使模块源码不直接引用 SSL/EVP 符号，链接期也必须能满足这两个库（否则 `cannot find -lssl`）。

## 处理策略（本仓库采纳：0 补丁 + 命令行变量钉死）

按模块逐条覆盖探测链入口，**不修改上游 Makefile**：

| 模块组 | 钉死手段 | 原理 |
|---|---|---|
| xml2 系 6 模块 | `XML2CFG=`（空值）+ `LOCALBASE=<libxml2 conan 前缀>` | 空值覆盖内部 `$(shell which …)` 赋值，强制走 `LOCALBASE/include/libxml2` + `-L$(LOCALBASE)/lib -lxml2` 回退分支 |
| ims_ipsec_pcscf | `BUILDER=`（空值）+ `LIBRARY_PATH=<libmnl 前缀>/lib` | 钉死 `-lmnl` 分支，链接路径由 `LIBRARY_PATH` 提供 |
| cdp | 显式声明 `openssl/<ver>` 依赖 + `LIBRARY_PATH` 含 openssl 前缀 | 满足恒真分支的 `-lssl -lcrypto` |
| 全模块 | `OS=harmonyos` + `extra_defs` 注入 linux 等价宏集 | 平台识别 + 语义等价；避免改上游源码 |

## 依赖形态核验（易误判点）

- conan 制品仓中的 `libmnl`、`openssl` 可能**只提供静态库**（`.a`，无 `.so`）。此时模块 `.so` 的 `DT_NEEDED` **不含**这两个库——符号静态内嵌。
- 因此消费者测试的"依赖闭包断言"**不能要求**运行时 `.so` 存在，应改为：核 `DT_NEEDED` 实际集合 + 核被引用符号是否已在模块内定义/静态内嵌。
- 判定命令：`readelf -d <module>.so | grep NEEDED`（比凭依赖清单推断可靠）。

## 禁止事项

- ❌ 用共享/宿主路径钉库（`XML2CFG=/usr/bin/xml2-config`、`LIBRARY_PATH=/usr/lib`）——污染构建机且掩盖依赖缺失。
- ❌ 只传 `LOCALBASE` 而不同时清空 `XML2CFG`/`BUILDER`——回退分支不会生效，属"看似修好实则仍走宿主探测"的假修复。
- ❌ 未核 `DT_NEEDED` 就把"依赖形态"写进文档（动态/静态判错会导致部署说明与产物不符）。

## 样例库（本仓库实证）

- `archives/k/kamailio-ims/6.0.6/`（16 模块；libxml2 ×6 + libmnl ×1 + cdp 的 openssl；0 补丁）
- `archives/k/kamailio-xml/6.0.6/`、`archives/k/kamailio-gcrypt/6.0.6/`、`archives/k/kamailio-unixodbc/6.0.6/`（同族单模块钉法）
