# Qt5 的 QtDBus 是运行期 dlopen 模式（-dbus）：“编译链接全绿、运行期连不上任何总线”，因为制品仓 dbus 包只提供静态库

> Draft: `DRAFT-MLITE-055-QT5-QTDBUS-RUNTIME-DLOPEN-LIBDBUS1-MISSING`
> Stem: `mlite-0.5.5-qt5-qtdbus-runtime-dlopen-libdbus1-missing` — pairs with the same-stem `.kv`

## 基本信息

- **ID**: DRAFT-MLITE-055-QT5-QTDBUS-RUNTIME-DLOPEN-LIBDBUS1-MISSING
- **严重度**: 3（3=🔴blocking / 2=🟡medium / 1=🟢minor）
- **类别**: runtime|qt5|dbus|dependency-defect
- **触发工具**: runtime
- **阶段**: runtime

## 错误特征

```
Cannot find libdbus-1 in your system|Not connected to D-Bus server|isConnected=0|libdbus-1
```

匹配关键词：`QtDBus, QDBusConnection, libdbus-1, qdbus_loadLibDBus, -dbus, -dbus-linked, Not connected to D-Bus server, 静态库, session bus`

## 根因

qt5-qtbase 配方用 configure `-dbus`（不等于 `-dbus-linked`）：libQt5DBus.so 通过 qdbus_loadLibDBus() 在运行期 dlopen “libdbus-1”，strings 可见 “Cannot find libdbus-1 in your system to resolve symbol”；而 ohpcd 的 dbus 包（含最新 1.14.10.2）只装 libdbus-1.a，全仓 find -name 'libdbus-1.so*' 命中 0 → dlopen 失败，QDBusConnection::sessionBus() 返回未连接（lastError=“Not connected to D-Bus server”）。DBusClientTestBase 之类的测试会以 “Failed to register mock D-Bus object … 'Not connected to D-Bus server'” 失败。

## 影响范围

所有使用 QtDBus 的 Qt5 包（通知、远程调用、跨进程 IPC）。编译/链接/打包全绿，只有跑运行期用例才暴露。注意：这与“设备上没有会话总线”是两个独立问题——补上共享 libdbus-1.so 后，用 conan dbus 包的 dbus-daemon 起总线即可让用例全绿（实测）。

## 验证命令

```bash
strings <qtbase_pkg>/lib/libQt5DBus.so | grep -i libdbus-1   # 命中 dlopen 名称；readelf -d libQt5DBus.so | grep NEEDED → 无 libdbus-1
```

## 处置建议

- **优先级**: 1
- **方案**: `ship-shared-libdbus-or-switch-to-dbus-linked`
- **说明**: (1) 依赖侧正解：dbus 包补 shared 构型（发布新版本）或 qt5-qtbase 改用 `-dbus-linked` 重新出包——两者任一即可让 QtDBus 真正可用；(2) 本地验证/绕行（不改变仓库）：用 dbus 包的静态库重链接出共享库后置于 LD_LIBRARY_PATH 前部：`clang -shared -Wl,--whole-archive libdbus-1.a -Wl,--no-whole-archive -o libdbus-1.so.3 -lexpat -lpthread`（本地 lld 会自动补 .codesign，可正常加载）；(3) 会话总线：OHOS 沙箱禁止 AF_UNIX bind 到 HMDFS（Operation not permitted），用 unix:tmpdir=<可写本地盘>；dbus 包自带 session.conf 的 EXTERNAL 认证在无 passwd 记录的环境会失败，需 <auth>ANONYMOUS</auth> + <allow_anonymous/>；(4) 注意 dbus/1.14.10.2 的 dbus-launch/dbus-run-session 内嵌构建期路径已失效，需用 dbus-daemon --config-file 显式启动。
- **参考命令**: `dbus-daemon --config-file=<anon-session.conf> --print-address --nofork`
- **可自动修复**: false

## 可复用知识总结（同类问题通用）

- **问题类**：Qt5 的 QtDBus 以 **`configure -dbus`**（运行期 `dlopen("libdbus-1")`）构建，而制品仓 dbus 只有静态库 → **编译链接全绿、运行期连不上任何总线**。
- **识别信号**：`QDBusConnection::sessionBus()` 返回未连接（`Not connected to D-Bus server`）；上游测试报 `Failed to register mock D-Bus object … 'Not connected to D-Bus server'`；`strings libQt5DBus.so | grep -i libdbus-1` 命中 `Cannot find libdbus-1 in your system…`；`readelf -d libQt5DBus.so | grep NEEDED` 无 `libdbus-1`。
- **通用处置**：① 依赖侧正解——让 dbus 提供 **shared** `libdbus-1.so`（发布新版本），或 qt5-qtbase 改用 **`-dbus-linked`**（静态 libdbus 并入 Qt5DBus，运行期不再 dlopen）；② 本地验证/绕行——用包内静态库重链接出共享库并置于 `LD_LIBRARY_PATH` 前部：`clang -shared -Wl,--whole-archive libdbus-1.a -Wl,--no-whole-archive -o libdbus-1.so.3 -lexpat -lpthread`（本地 lld 会自动补 `.codesign`，可立即加载），实测 5/5 + 3/3 用例全绿；③ 会话总线：OHOS 沙箱禁止在 HMDFS 上 `bind` AF_UNIX（需 `unix:tmpdir=<可写本地盘>`），且包内 `session.conf` 的 `EXTERNAL` 认证在无 passwd 记录的环境会失败（需 `<auth>ANONYMOUS</auth>`+`<allow_anonymous/>`）；④ `dbus-launch`/`dbus-run-session` 若内嵌构建期路径失效，改用 `dbus-daemon --config-file=… --print-address --nofork`。
- **适用范围**：所有依赖 QtDBus 的 Qt5 包，以及任何"运行期 dlopen 外部库"的依赖组合（判据：`strings` + `NEEDED` 双查）。
