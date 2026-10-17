# DRAFT: OHOS qtbase 的 Qt6DBus 运行时 dlopen libdbus-1 共享库而制品生态仅静态库，应为 dlopen 消费方提供（vendored）共享 libdbus-1

- **草稿 ID**: `DRAFT-qtdbus-dlopen-libdbus-static-only-registry`
- **来源**: kglobalacceld-6.7.2 适配 run（vendored libdbus-1.so.3；失败证据 ci05 log，修复对照 ci10 起 3/3 PASS）
- **状态**: DRAFT（随 kglobalacceld feat 分支交付，待主编/AI 审核提升为 E 条目）
- **配套文件**: `knowledge/drafts/DRAFT-qtdbus-dlopen-libdbus-static-only-registry.kv`（同 stem 配对）
- **申报域**: 依赖闭包（dependency）｜分层 **L1**（制品形态语义 × Qt 运行时装载机制，单库可申报）

## 问题现象

Qt6::DBus 消费者（kglobalacceld 守护进程/autotests）在 OHOS 真机上连接**任何**
D-Bus 总线（含已验证存活的 TCP 会话总线）恒失败：

```
kf.dbusaddons: DBus session bus not found. To circumvent this problem try the following command (with bash):
    export $(dbus-launch)
```

随后 `KGlobalAccelD::init()` 的 `QDBusConnection::sessionBus().registerObject/registerService`
返回 false（shortcutstest init FALSE、allowlisttest SIGSEGV——ci05）。
症状指向总线层，极易误诊；实为客户端库装载层问题。

## 根因

1. **qtbase-sql-dbus/6.11.1 以 dbus-linked=OFF 构建 Qt6DBus**：`libQt6DBus.so`
   的 DT_NEEDED 仅 `libQt6Core/libc++_shared/libc`，不含 libdbus——Qt 在运行时
   按名字 `dlopen("libdbus-1" + soname 后缀)` 装载 libdbus
   （`qdbus_loadLibDBus` 机制）。
2. **llvm-strings 实证**（toybox `grep -a` 在该 .so 上找不到该字符串，必须用
   `/storage/Users/currentUser/.harmonybrew/bin/llvm-strings`）：

   ```
   libdbus-1
   Cannot resolve '%s' in your libdbus-1.
   Cannot find libdbus-1 in your system to resolve symbol '%s'.
   ```

3. **制品仓 dbus 全系仅静态库**：dbus/1.14.10、1.14.10.1、1.14.10.2 的包
   `lib/` 均只有 `libdbus-1.a`，共享库计数 = 0 → dlopen 失败 →
   `QDBusConnection::sessionBus()` 返回无效连接。
4. **修复**：消费方 recipe 内以官方 dbus 1.14.10 源码（URL+SHA256 固定）构建
   客户端共享库（`BUILD_SHARED_LIBS=ON`、仅 `dbus-1` target、
   `CMAKE_SYSTEM_NAME=OHOS` 走 UNIX 分支），产物 NEEDED 仅 libc（无 expat），
   随包发布至 `lib/` 并入 LD_LIBRARY_PATH → ci10 起 3/3 PASS，
   test_ohos_daemon 7 断言全过（ci05 → ci10 对照）。

## 方案空间

- **rec_*（主方案）**：dlopen 消费方场景下，为消费链提供共享 libdbus-1（包内
  vendored 官方源码构建，或等制品仓发布 shared dbus 包后改用制品）。
- **fallback_1**：制品仓发布 shared-lib dbus 包后移除 vendored 拷贝（长期修复，
  kglobalacceld notes.md 已声明移除条件）。
- **fallback_2**：若某消费者可改用 dbus-linked=ON 的 Qt 构建（重发 qtbase），
  可静态链入——超出本 run 边界，仅作生态级退路记录。

### 与 E277 forbid_2 的调和（场景边界澄清，非违反）

E277 forbid_2（"禁止动态链接 vendored 依赖，应静态链接进主库"）的适用前提是
**链接时消费方**——vendored 库可参与链接闭包、静态代偿可行。本条消费方是
**Qt6DBus 的运行时 dlopen**：按名字装载共享对象，静态库在机制上无法被 dlopen
消费，不存在"静态代偿"选项，故 forbid_2 在 dlopen 消费方场景不适用。同时诚实
写下本方案代价（即 forbid_2 所警示的两点）：

1. vendored `libdbus-1.so.3` 随包发布需纳入 OHOS 代码签名与 LD_LIBRARY_PATH
   管理（本 run 由 recipe 统一打包规避）；
2. 与未来制品仓 shared dbus 包并存时会符号/版本撞车，移除条件已写入
   kglobalacceld notes.md。

### 禁止模式

- `forbid_1`：`patchelf` 后改 ELF 补 dlopen 依赖——E537/E073 实证 HMDFS 拒绝
  对改写文件 mmap PROT_EXEC；运行时 Permission denied。
- `forbid_2`：把 vendored 静态 `libdbus-1.a` 交给 dlopen 消费方或试图"静态链
  接进 Qt6DBus"——dlopen 按名字装载共享对象，静态库机制上不可消费（本条与
  E277 forbid_2 的场景分界：链接时消费方才可静态代偿）；DBus 连接持续无效，
  症状不变。
- `forbid_3`：症状导向修复（重装/重启 dbus-daemon、改总线地址）——根因在
  dlopen 层不在总线层；掩盖真实缺口，误导后续 run。

## 验证证据（自包含探针，llvm-strings/llvm-nm，已设备实测）

```sh
LS=/storage/Users/currentUser/.harmonybrew/bin/llvm-strings
# 陷阱：toybox grep -a 在该 .so 上找不到 libdbus-1 字符串，必须用 llvm-strings/llvm-nm；
# 且 dbus=OFF 的 qtbase 副本无 libdbus-1 字符串（qtbas569625… 副本实测零命中），
# 必须取 qtbase-sql-dbus 包的 libQt6DBus.so（qtbas8115…/qtbasaa55… 副本已验证命中）。
# 1) 证 Qt6DBus 为运行时 dlopen 消费方（dbus-linked=OFF）：
$LS /storage/Users/currentUser/.conan2/p/qtbas811589fa3a1fb/p/lib/libQt6DBus.so \
  | grep -E 'libdbus-1|Cannot resolve .* your libdbus-1'
#   预期命中: libdbus-1 / Cannot resolve '%s' in your libdbus-1. /
#             Cannot find libdbus-1 in your system to resolve symbol '%s'.
# 2) 证制品生态无共享 libdbus：
ls /storage/Users/currentUser/.conan2/p/dbus*/p/lib/ | grep -c '\.so'    # =0（仅 libdbus-1.a）
# 3) 运行失败复现：不挂 vendored 库，跑任一 Qt6DBus 消费者
#   → kf.dbusaddons: DBus session bus not found（尽管 dbus-daemon TCP 会话总线存活）；
#   挂上包内 libdbus-1.so.3 后同命令成功（kglobalacceld run ci05 → ci10 对照）。
```

## 四范围多轴查重

检索范围：`knowledge/graph/index.tsv` + `knowledge/drafts/` + 经验仓（grep
libdbus/dlopen 零命中）；检索词：dbus、dlopen、libdbus、vendored、static-only、
session bus。

| 近邻条目 | 逐项差异 |
|---|---|
| DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime | 总线**守护进程运行层**（AF_UNIX EPERM→TCP+passwd shim+allow_anonymous）；本条是**客户端库层**（dlopen 共享库缺失），两层层叠不重叠 |
| E277 | 通用 vendored 工程模式（L2），无 Qt6DBus dlopen 机理；其 forbid_2 已按上文显式调和——dlopen 消费方为场景例外 |
| E073/E537/E212 | symlink 不可装载 / DT_NEEDED 绝对路径 / 安全标签面，与"生态无共享库可 dlopen"不同 |

**新增价值**：任何消费 Qt6::DBus 的包在本生态必中；症状（bus not found）与根
因（dlopen 失败）距离远，诊断价值高。

## 适用边界

- 适用：任何消费 Qt6::DBus 的 Conan 包/应用（OHOS qtbase dbus-linked=OFF 生态）；
  凡"Qt6DBus 消费者连接任何总线恒失败"即应先探针本条。
- 不适用：dbus-linked=ON 的 Qt 构建（直接静态链入）；非 Qt 的 D-Bus 客户端
  （libdbus 直接链接，链接时消费方适用 E277 原语义）。

## 关键词

Qt6DBus, dbus-linked, dlopen, libdbus-1.so.3, libdbus-1.a, 静态库, 共享库,
vendored, DBus session bus not found, QDBusConnection invalid,
qtbase-sql-dbus, session bus shim, 注册失败, kglobalacceld

## 挂钩

- `similar_to`: E277, DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime
- `principles`: real-evidence-over-assumption, link-time-fix-over-postprocess, relocatability-preserving, declared-dependency-metadata
