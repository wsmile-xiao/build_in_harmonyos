# draft-qtwayland-6.11.1-qt-tests-deep-path-socket-tmpdir-qpa

## 症状

qtwayland 6.11.1 上游测试（QT_BUILD_TESTS=ON，2 个 qt_internal_add_test 目标）在
OHOS aarch64 设备直跑 ctest 时三重失败：

```
# 失败一：socket 路径超限（QFATAL abort）
error: socket path "/storage/Users/currentUser/.conan2/p/b/<hash>/b/build/Release/test_results/qt_temp-XXXXXX/wayland-0" plus null terminator exceeds 108 bytes
QFATAL : tst_WaylandCompositor::seatCapabilities() Fatal: Failed to open server socket: "wayland-qt-test-0"

# 失败二：shm buffer 无法创建（只读 /tmp）
QWARN  : tst_WaylandCompositor::inputRegion() open /tmp/wayland-shm-XXXXXX failed: Read-only file system
FAIL!  : tst_WaylandCompositor::inputRegion() 'waylandSurface->inputRegionContains(QPoint(1, 2))' returned FALSE

# 失败三：QPA 平台冲突
qt.qpa.plugin: Could not load the Qt platform plugin "wayland" in "" even though it was found.
```

## 根因

Qt 上游测试在 OHOS 独立构建环境的三重平台冲突：

1. **108 字节 socket 路径上限**：POSIX Unix domain socket 的 sun_path 上限 108 字节。
   conan 缓存构建目录（`~/.conan2/p/b/<hash>/b/build/Release`）路径深度必然超限——
   libwayland 报 "socket path ... plus null terminator exceeds 108 bytes" 后 QFATAL
   abort。且 **QtTest 的 ctest wrapper 自行用 TMPDIR 生成 qt_temp-XXXXXX 目录**存放
   per-test XDG_RUNTIME_DIR，TMPDIR 指向深路径时同样超限（即使你已给 ctest 设了浅的
   XDG_RUNTIME_DIR 也会被 wrapper 的 qt_temp 覆盖）。

2. **/tmp 只读**：OHOS 的 /tmp 挂载只读文件系统（EROFS），上游 mock client 的
   ShmBuffer 用硬编码 `/tmp/wayland-shm-XXXXXX` 调 mkstemp，所有 buffer 型用例
   （inputRegion/mapSurface/frameCallback 等十余个）失败。

3. **QPA 平台双分离**：Qt Wayland 的两类测试 main 宏对 QPA 平台要求相反——
   client 侧测试（QCOMPOSITOR_TEST_MAIN 强制 `QT_QPA_PLATFORM=wayland`，连进程内
   mock compositor，需要 QT_PLUGIN_PATH 含本包构建的 ivi-shell 插件）与 compositor
   侧测试（QTEST_MAIN + QGuiApplication 用 offscreen，自身在进程内创建 wl_display
   服务端）。单一环境的 ctest 调用无法同时满足两者。

**附关键可行性发现**：qtbase/6.11.1.2 conan 包自带 `libexec/qtwaylandscanner` 与
`Qt6WaylandScannerTools` CMake 包——`QT_FEATURE_wayland_server` 特性在 standalone
构建即可启用（此前普遍误判为"仅 qtbase 超级构建提供"），这使 compositor 模块与其
49 个上游用例可构建可执行。

## 修复

conanfile.py build() 内组合修复（四件套）：

```python
# ① 短路径 runtime dir（108 字节限制）——不能用 build_folder 下的深路径
short_tmp = (
    _tmp
    if len(_tmp := os.environ.get("TMPDIR", "/data/storage/el2/base/temp")) <= 40
    else "/data/storage/el2/base/temp"
)
runtime_dir = os.path.join(short_tmp, "qtwayland-{}-xdg".format(os.getpid()))
os.makedirs(runtime_dir, exist_ok=True)
os.chmod(runtime_dir, 0o700)  # XDG 规范要求 700

# ② TMPDIR 同样指向短路径（QtTest wrapper 的 qt_temp 会继承）
common_env = ('XDG_RUNTIME_DIR="{rd}" XKB_CONFIG_ROOT="{xkbcfg}" '
              'QT_PLUGIN_PATH="{plugins}" TMPDIR="{tmpdir}" LD_LIBRARY_PATH="{lp}"'
              ).format(..., tmpdir=short_tmp, ...)

# ③ 双 QPA 平台分跑：每测试一次 ctest 调用
for test_name, qpa in (
    ("tst_client_iviapplication", "wayland"),   # 连进程内 mock compositor
    ("tst_compositor", "offscreen"),            # 自建 wl_display 服务端
):
    self.run('QT_QPA_PLATFORM={qpa} {env} ctest --test-dir "{bf}" '
             '--output-on-failure --timeout 300 -R "^{tn}$" ...')

# ④ XKB_CONFIG_ROOT 指向 qtbase 包的 xkb 数据（键盘用例 keymap）
xkbcfg=os.path.join(qtbase_pkg, "share", "X11", "xkb")
```

上游测试源码补丁（/tmp 只读）：

```diff
-    char filename[] = "/tmp/wayland-shm-XXXXXX";
+    // HarmonyOS mounts a read-only filesystem on /tmp; honor TMPDIR
+    QByteArray tmpDir = qgetenv("TMPDIR");
+    if (tmpDir.isEmpty())
+        tmpDir = QByteArrayLiteral("/tmp");
+    QByteArray pattern = tmpDir + QByteArrayLiteral("/wayland-shm-XXXXXX");
+    char *filename = pattern.data();
```

配套：`QT_FEATURE_wayland_server=ON`（qtbase 包自带 qtwaylandscanner）+ 新增直接依赖
`libxkbcommon/1.6.0`（tst_compositor 键盘用例的 XKB::XKB，经修正 prefix 的
xkbcommon.pc 解析——libxkbcommon 包无 cmake config，qtbase 的 FindXKB 走 pkg-config）。

## 验证

- 修复前：同环境 100% 复现三重失败（socket 超限 abort + shm EROFS + QPA abort）
- 修复后：conan create 全绿——本地 ctest 2/2 Passed（tst_client_iviapplication
  5/5 执行项 + tst_compositor 53/53 执行项 = 58/58 100%，覆盖上游全部 52 个用例函数）
- CI #49189 通过（2026-09-17）

## 适用范围

- 所有需要在 conan build 目录内运行 Wayland/Unix socket 类测试的 Qt 模块
  （qtwayland 及后续依赖 Wayland 的 Qt 模块）；
- 所有上游测试硬编码 /tmp 临时文件且需在 OHOS 跑的包（配合 E002）；
- 所有 QtTest wrapper（qt_temp 机制）与深路径 conan 缓存组合的包。
