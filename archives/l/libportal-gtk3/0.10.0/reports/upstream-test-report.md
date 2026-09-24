# libportal-gtk3 0.10.0 上游测试用例本地真实执行报告

> 修复 PR #10967 rule4 FAIL（上游 85 用例 0/85 未执行 + 少报 N=85>81）。
> 审查口径："无论任何理由均不通过"——本地真实执行上游测试用例，实测数据入正文。

## 执行结论（Septest 85 口径）

| 指标 | 数值 |
|------|------|
| 上游用例总数 N | **85**（pytest 81 + portal-test 四后端 4） |
| 本地真实执行 | **82 / 85**（96.5%） |
| 真实通过 | **67**（pytest 66 + portal-test-gtk3 链接验证 1） |
| 真实失败（平台 fd 传递语义差异，逐项定性见下） | **15** |
| 未执行（环境豁免，逐项理由） | **3**（portal-test-gtk4/qt5/qt6） |

- 执行框架：上游 tests/pyportaltest 原版 pytest 套件（上游测试源码零修改，仅新增
  tests/conftest.py 平台适配——dbusmock 临时 bus 重定向到外部 TCP session bus，
  与主件 libportal/0.10.0（PR #10103，已合入）同一方案）
- 全量复跑两轮：`15 failed, 66 passed in 110.07s` / `15 failed, 66 passed in 155.18s`
  ——失败集合与分模块结果完全相同，可复现
- portal-test-gtk3 链接验证 3 次复跑全部 exit 0

## 分模块明细（pytest 81）

| 测试文件 | 用例数 | 通过 | 失败 | 通过率 |
|----------|--------|------|------|--------|
| test_inputcapture.py | 35 | 33 | 2 | 94.3% |
| test_notification.py | 13 | 9 | 4 | 69.2% |
| test_remotedesktop.py | 19 | 15 | 4 | 78.9% |
| test_screencast.py | 6 | 1 | 5 | 16.7% |
| test_wallpaper.py | 8 | 8 | 0 | 100% |
| **pytest 合计** | **81** | **66** | **15** | **81.5%** |

## 15 个失败用例逐项定性

**根因（单一，与主件 PR #10103 实测一致）**：OHOS 上 D-Bus unix-fd
（SCM_RIGHTS 句柄投递）语义与 Linux 存在差异——libportal 的 Session/EIS/
notification-icon 路径通过 GDBus `GUnixFDList` 向客户端回传管道 fd，本平台
fd 跨进程投递后不可用：

1. `ValueError: negative file descriptor`（9 例）——fdlist 返回无效描述符
2. `GDBus.Error:org.freedesktop.DBus.Python.MemoryError`（mock 端 send_message
   带 fdlist 失败，3 例 connect_to_eis 系）
3. `assert 0 == 1`（notification icon/sound 4 例）——icon 经 `file-descriptor`
   变体传输，fd 不可读导致 mock 收到的 notification 缺 icon 项

逐项清单（15 例，同一根因、三类表现）：

| # | 用例 | 失败表现 |
|---|------|---------|
| 1 | TestInputCapture::test_connect_to_eis | GDBus.Error Python.MemoryError（mock 端 fdlist 回传失败） |
| 2 | TestInputCapture::test_connect_to_eis_session2 | 同上 |
| 3 | TestNotification::test_add_notification_bytes_icon | assert 0 == 1（icon 走 file-descriptor 变体） |
| 4 | TestNotification::test_add_notification_bytes_sound | 同上（sound 走 file-descriptor 变体） |
| 5 | TestNotification::test_add_notification_file_icon | 同上 |
| 6 | TestNotification::test_add_notification_file_sound | 同上 |
| 7 | TestRemoteDesktop::test_connect_to_eis | GDBus.Error Python.MemoryError |
| 8 | TestRemoteDesktop::test_connect_to_eis_fail_reconnect | 同上 |
| 9 | TestRemoteDesktop::test_create_session | ValueError: negative file descriptor |
| 10 | TestRemoteDesktop::test_create_session_restore | 同上 |
| 11 | TestScreenCast::test_close_session | 同上 |
| 12 | TestScreenCast::test_create_session | 同上 |
| 13 | TestScreenCast::test_create_session_v3 | 同上 |
| 14 | TestScreenCast::test_session_restore_token_null_if_not_started | 同上 |
| 15 | TestScreenCast::test_session_start | 同上 |

**定性：平台环境差异（OHOS unix-fd 投递），非库缺陷**。证据：
- 同组无 fd 交互的用例全部通过（inputcapture 35 例中 33 例通过，含 zones/
  barriers 全交互路径；wallpaper 8/8 全过；notification 的纯文本路径 9/13 过）
- 失败发生在纯软件栈（python-dbus ↔ dbus-daemon ↔ GDBus）的 fdlist 投递
  环节，与 libportal-gtk3 业务逻辑无关——本包交付的 xdp_parent_new_gtk 等
  GTK3 后端 API 不涉及 fd 传递路径
- 与主件 libportal/0.10.0（PR #10103，同一 mock 栈同一 D-Bus 实现）实测的
  失败集合逐项一致（66/81 相同通过集），两 PR 各自独立两轮复现

**不修改上游测试、不豁免计数**：15 例计入失败并以真实结果申报（66/81 通过率 81.5%）。

## portal-test 四后端处理（Septest 85 口径补齐 4 项）

portal-test/ 是上游 `-Dportal-tests=true` 时构建的各后端**示例/链接验证程序**
（meson `run_target`/`executable`，不在 `meson test` 注册列表——上游 CI 的
`meson test --verbose` 也只执行 pytest + qt5 + qt6 三个注册项）：

| 项 | 处理 | 结果 |
|----|------|------|
| portal-test-gtk3（本件后端） | **真实执行**：上游 portal-test/gtk3/portal-linking-test.c（`xdp_portal_new()` + `xdp_portal_is_camera_present()`）以本 PR 交付的 libportal-gtk3/0.10.0 包 + libportal/0.10.0 主件包 + gtk/3.24.43 全链编译链接运行 | **PASS**（exit 0，TCP session bus 上 XdpPortal 构造成功；3 次复跑一致；链接全链：-lportal-gtk3 -lgtk-3 -lportal -lgio-2.0 等 30+ 库零 undefined symbol） |
| portal-test-gtk4 | backend-gtk4=disabled（本件仅交付 gtk3 后端），上游 meson 条件不构建；且 gtk4 门户测试强制要求 introspection（gtk4/meson.build: `error('The GTK4 test portal requires introspection')`） | 豁免（不注册） |
| portal-test-qt5 | backend-qt5=disabled，上游 meson 条件不构建（`if 'qt5' in enabled_backends`） | 豁免（不注册） |
| portal-test-qt6 | backend-qt6=disabled，同上 | 豁免（不注册） |

注：portal-test-gtk3 主程序（portal-test-gtk3 GUI 示例）依赖 gstreamer-audio-1.0
与图形显示，OHOS broadway 后端无 X11/Wayland 显示环境，本机无 gstreamer——
上游 meson `run_target('portal-test-gtk3')` 交互式程序在上游 CI 也仅构建不
执行；以同目录 portal-linking-test-gtk3（上游专为链接验证编写的程序）真实
执行作为该后端的测试证据。

## 本地执行环境（OHOS aarch64 原生，全程真实运行）

与主件 PR #10103 相同的环境方案（复用其已验证组件），针对本件补齐 libffi
static trampolines 关键修复：

1. **D-Bus session bus**：conan `dbus/1.14.10.1` dbus-daemon，TCP 监听
   （`tcp:host=127.0.0.1,port=19876`）——OHOS SELinux 对 shell 域进程的
   unix domain socket 监听/连接受限，TCP 通道语义等价
2. **python-dbus 1.4.0 本地重编**：`_dbus_bindings`/`_dbus_glib_bindings`
   动态链接本地自编 libdbus-1.so（dbus 1.14.10 cmake 共享库构建）+ conan
   glib/2.84.0.1（与 PyGObject 同一 glib 实例，规避双 glib GType 冲突）
3. **python-dbusmock 0.32.1**（PyPI python-dbusmock sdist，纯 Python）
4. **PyGObject 3.58.0 本地重编**：`gi/_gi` 动态链接 conan
   girepository-2.0 + libpython3.12；**libffi 3.4.4 重编启用
   FFI_EXEC_STATIC_TRAMP（static trampolines）并 patch tramp_table_map 为
   匿名内存拷贝方案**——OHOS SELinux 拒绝 file-backed exec 映射
   （MAP_FIXED|PROT_EXEC Permission denied 实测），静态蹦床默认从 libffi
   so 文件映射代码表在 OHOS 不可行；改为 memcpy 蹦床代码到匿名 RW 页 +
   `__builtin___clear_cache` 刷 I-cache + mprotect RX，parm 表紧邻布局
   保持上游 `adr x17, #16376` 相对寻址语义——closure 分配与回调全链修复
   （`GLib.timeout_add` 回调真实触发验证）
5. **typelib 链**：GLib/GObject/Gio/GModule/GioUnix/GLibUnix 2.84 typelib
   （Debian gir1.2-glib-2.0 2.84.4 数据包 arm64 预编译）+ conan
   gobject-introspection/1.78.1 的 g-ir-scanner（giscanner 模块 + ldd shim）
   对本 PR 同源码（SHA256 一致）meson `-Dintrospection=true` 真实构建
   Xdp-1.0.gir → g-ir-compiler 编译 Xdp-1.0.typelib——测试经
   `gi.require_version("Xdp","1.0")` 调用真实 libportal.so API
6. **测试适配（唯一新增文件 tests/conftest.py，上游测试源码零修改）**：
   dbusmock `PrivateDBus.start()` 重定向到外部 TCP bus

verbose 全量输出两轮本地留存（*.log 按项目文件规范不入库，主件 PR #10103 同口径），统计与逐项定性以本报告为准。

执行命令（上游 tests/ 目录）：
```
python3 -m pytest pyportaltest/ -v
# → 两轮：66 passed, 15 failed（110.07s / 155.18s，失败集合相同）
clang ... portal-test/gtk3/portal-linking-test.c $(pkg-config --cflags --libs libportal-gtk3)
# → portal-linking-test-gtk3 exit 0（3 次复跑一致）
```
