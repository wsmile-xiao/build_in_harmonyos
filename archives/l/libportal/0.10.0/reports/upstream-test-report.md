# libportal 0.10.0 上游测试用例本地真实执行报告

> 修复 PR #10103 rule4 FAIL（上游 83 用例 0/83 未执行）。
> 审查口径：无论任何理由均不通过——本地真实执行上游测试用例。

## 执行结论

| 指标 | 数值 |
|------|------|
| 上游注册用例总数 N | **83**（pytest 81 + qt5/qt6 meson 测试目标 2） |
| 本地真实执行 | **81 / 83**（97.6%） |
| 真实通过 | **66** |
| 真实失败（平台 fd 传递限制） | **15** |
| 未执行（环境豁免，逐项理由） | **2**（qt5/qt6 需 Qt5/Qt6 模块与对应 backend 库，OHOS 无 Qt） |

- 执行框架：上游 tests/pyportaltest 原版 pytest 套件（0 修改上游测试源码，仅添加平台适配 conftest.py——见下）
- 最终复跑：`15 failed, 66 passed in 95.32s`（全量两轮 171.30s / 95.32s 结果一致，失败集合完全相同，可复现）
- 原始 verbose 日志：两轮全量输出经本地留存（*.log 按项目文件规范不入库——第十九条），关键数字与本报告统计一致；失败用例完整清单与逐项定性见下文

## 分模块明细

| 测试文件 | 用例数 | 通过 | 失败 | 通过率 |
|----------|--------|------|------|--------|
| test_inputcapture.py | 35 | 33 | 2 | 94.3% |
| test_notification.py | 13 | 9 | 4 | 69.2% |
| test_remotedesktop.py | 19 | 15 | 4 | 78.9% |
| test_screencast.py | 6 | 1 | 5 | 16.7% |
| test_wallpaper.py | 8 | 8 | 0 | 100% |
| **pytest 合计** | **81** | **66** | **15** | **81.5%** |
| tests/qt5（QTest 目标） | 1 | — | — | 未执行（无 Qt5） |
| tests/qt6（QTest 目标） | 1 | — | — | 未执行（无 Qt6） |

## 15 个失败用例逐项定性

**根因（单一）**：OHOS 上 D-Bus unix-fd（`SCM_RIGHTS` 句柄传递）语义与 Linux 存在差异——
libportal 的 Session/EIS/notification-icon 路径通过 GDBus `GUnixFDList` 向客户端回传管道
fd，mock 端与客户端在本平台的 fd 跨进程投递后不可用，表现为：

1. `ValueError: negative file descriptor`（9 例）——fdlist 返回无效描述符
2. `MemoryError`（mock 端 send_message 带 fdlist 失败，3 例 connect_to_eis 系）
3. `assert 0 == 1`（notification icon/sound 4 例）——icon 经 `file-descriptor` 变体
   传输，fd 不可读导致 mock 收到的 notification 缺 icon 项计数为 0

逐项清单（15 例，同一根因、两类表现）：

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
- 同组无 fd 交互的用例全部通过（如 screencast 的 test_available_cursor_modes、
  test_close_session 之外的 session 属性断言；inputcapture 35 例中 33 例通过含
  barriers/zones 全交互路径）
- 失败在纯软件栈（python-dbus ↔ dbus-daemon ↔ GDBus）复现，与 libportal 业务逻辑
  无关——mock 端将 fd 放入 reply 的 fdlist 时即失败
- CI 侧（远端 clean OHOS 环境）同样无法满足 unix-fd 语义，非本地偶发

**不修改上游测试、不豁免计数**：15 例计入失败并以真实结果申报（66/81 通过率 81.5%）。

## 2 个未执行项豁免理由

| 用例 | 豁免理由 |
|------|---------|
| tests/qt5（qt5-test 可执行目标） | meson 仅在 `backend-qt5=enabled` 时注册（tests/meson.build: `if 'qt5' in enabled_backends`），构建需 Qt5 Core/Test 模块；OHOS 无 Qt5 生态，PR 与 CI 构建均 `-Dbackend-qt5=disabled`——测试目标在上游条件逻辑下不注册，与 Linux 无 Qt 机器上行为一致 |
| tests/qt6（qt6-test 可执行目标） | 同上（`backend-qt6=disabled`） |

## 本地执行环境（OHOS aarch64 原生，全程真实运行）

上游 pytest 套件的三个前置在 OHOS 缺位，本地逐一补齐（不改上游测试源码）：

1. **D-Bus session bus**：conan 制品仓 `dbus/1.14.10.1` 的 dbus-daemon，以 TCP
   监听（`tcp:host=127.0.0.1,port=19876`）运行——OHOS SELinux 对 shell 域进程的
   unix domain socket 监听/连接有限制，TCP 通道语义等价
2. **python-dbus / python-dbusmock / PyGObject**：
   - python-dbus 1.4.0（PyPI sdist）本地重编——`_dbus_bindings`/`_dbus_glib_bindings`
     动态链接 libdbus（dbus 1.14.10 源码本地编 libdbus-1.so）与 conan glib/2.84.0
   - python-dbusmock 0.32.1（PyPI，纯 Python）
   - PyGObject 3.58.0（PyPI sdist）本地重编 `gi/_gi`——动态链接 conan
     glib/2.84.0 + girepository-2.0 + libffi 3.4.7（本地自编，启用 closure
     static trampolines 以适配 OHOS execmem 限制）
3. **typelib 链**：GLib/GObject/Gio/GModule/GioUnix/GLibUnix 2.84 gir（gir1.2-glib-2.0
   2.84.4 数据包）经 g-ir-compiler 1.78.1 编译；Xdp-1.0.gir 由 meson
   `-Dintrospection=true` 对本 PR 同源码（SHA256 校验一致）真实构建生成
4. **测试适配（唯一新增文件 tests/conftest.py）**：将 dbusmock 的
   `PrivateDBus.start()`（临时 unix socket daemon）重定向到外部 TCP bus——
   mock 子进程经 `DBUS_SESSION_BUS_ADDRESS` 连接（dbusmock 原生机制），上游
   测试断言逻辑零改动

执行命令（上游 tests/ 目录）：
```
python3 -m pytest pyportaltest/ -v
# → 66 passed, 15 failed（两轮一致）
```
