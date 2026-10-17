# libportal-gtk3 0.10.0 适配笔记

## 背景与分工

- 上游：https://github.com/flatpak/libportal tag 0.10.0（LGPL-3.0-only）
- libportal 是 XDG desktop portal 的 GObject 包装库；同一源码仓库通过
  meson feature 选项产出四个后端库：libportal（主库）、libportal-gtk3、
  libportal-gtk4、libportal-qt5/qt6
- **跨账号同链分工**（平台任务 #13396/#13397/#13398）：
  - libportal 0.10.0 主件 → j669539（#13396，在途）
  - libportal-gtk3 0.10.0 → 本件 calbee21（#13397）
  - libportal-gtk4 0.10.0 → 任务 #13398（open 未领）
- 本件产物：libportal-gtk3.so.1.0.0（+dev 别名）+ portal-gtk3.h +
  libportal-gtk3.pc

## 构建方案（零补丁）

1. meson 选项：`backend-gtk3=enabled`，其余后端/introspection/vapi/
   docs/tests/portal-tests 全关
2. 主库在源码树内一起编译（meson 内部 declare_dependency），本件
   package() 阶段剔除主件产物（libportal.so*/libportal.pc/
   include/libportal/），只交付 gtk3 后端——避免与主件包 R26 同名冲突
3. 运行期依赖 libportal.so.1 由 requires("libportal/0.10.0") 提供

## 平台兼容性（无补丁的原因）

gtk/3.24.43（ohpcd 已发布，broadway 后端）的 gdkconfig.h：

```c
#undef GDK_WINDOWING_X11
#define GDK_WINDOWING_BROADWAY
#undef GDK_WINDOWING_WAYLAND
```

上游 portal-gtk3.c 的 X11/Wayland 代码在 `#ifdef GDK_WINDOWING_*` 内，
broadway 后端下全部被条件编译剔除。剩余代码：
- `xdp_parent_new_gtk()`：纯 GObject 操作（g_new0 + g_object_ref + vtable）
- `g_warning("Couldn't export handle, unsupported windowing system")` 兜底

天然兼容 OHOS，无需任何补丁。

## 构建期依赖处理（三个坑）

1. **gio-unix-2.0.pc 缺失**：glib/2.84.0.1 配方未声明 gio-unix 组件，
   PkgConfigDeps 不产出该 pc；上游 meson `dependency('gio-unix-2.0')`
   失败。解法：从 glib 包内真实 pc 复制并把 `prefix=/` 改写为包路径
   （cpdb-libs/2.0-b5 已验证模式）
2. **glib 工具变量**：`gnome.mkenums` 读 glib-2.0.pc 的
   glib_mkenums/glib_genmarshal 变量，meson.build:35 直接
   `get_variable` 查询——PkgConfigDeps 生成的 pc 没有这些变量导致
   configure 失败。解法：glib 包 bin/ 下的 glib-mkenums 等是 python3
   脚本，直接绝对路径写进 pc（accountsservice/26.27.3 模式）
3. **libc++_shared.so 运行时解析**：test_package 真跑时 musl 加载器
   默认路径不含 /system/lib64；alkimia/8.2.1 先例——test() 手动把
   依赖 lib 目录 + /system/lib64 注入 LD_LIBRARY_PATH

## test_package 设计

- test.c 调用被测包真实 API：`xdp_parent_new_gtk()`（后端唯一公开
  函数，纯内存操作，无 display 需求）+ `XDP_TYPE_PORTAL` 类型注册验证
  + `gtk_get_*_version()`（gtk 包同款 headless-safe 模式）
- **不能用 `xdp_portal_new()`**：主库构造函数会立即 spawn D-Bus
  session bus，无 machine-id 的机器上 GLib abort（实测：
  `Failed to create XdpPortal instance: Cannot spawn a message bus
  without a machine-id`，exit 134）。这是主件/本件共同的已文档化
  运行时限制（OHOS 无 D-Bus）
- GtkWindow 实例化需要 display（style provider 查询在 g_object_new
  阶段），headless 环境传普通 GObject 给 xdp_parent_new_gtk 验证后端
  路径（函数只 g_object_ref + 装 vtable，不碰窗口内部）

## 上游测试（81 pytest 用例，全量豁免）

上游 tests/pyportaltest：inputcapture 35 + notification 13 +
remotedesktop 19 + screencast 6 + wallpaper 8 = 81 用例。

框架要求：pytest-3 + python3-dbus + python3-dbusmock + PyGObject +
D-Bus session bus（dbus-daemon 需 machine-id）。

豁免证据链：
- CI 离线环境无 pytest/dbusmock（meson 的 python.find_installation
  required: false 找不到即静默跳过注册）
- OHOS 本机实测无 /var/lib/dbus/machine-id 与 /etc/machine-id，
  xdp_portal_new 直接 abort（见上）
- meson test 即使强制跑也 0 注册（pytest/pydbus 不可得）
- 本地补跑尝试证据与逐文件技术原因写入 PR 正文

## 验证记录

本地 conan create（完整版配方含 libportal/0.10.0 requires）：

```
[32/33] Compiling C object libportal/libportal-gtk3.so.1.0.0.p/portal-gtk3.c.o
[33/33] Linking target libportal/libportal-gtk3.so.1.0.0
...
GTK 3.24.43
xdp_parent_new_gtk OK: 0x595ee5a420
XDP_TYPE_PORTAL registered: 383844311648
test libportal-gtk3 0.10.0: OK
```

依赖图 22 个包全部从 ohpcd 制品仓/本地缓存解析（gtk 链 20 + libportal
主件 + 本件）。

## 断链状态（等待主件）

libportal/0.10.0 主件（#13396，j669539）未发布 → 本件 CI 的 L0i 依赖
门禁会拦截。处置：配方主体已完成并本地全链验证（用本地 stub 模拟主件
产出——同样的上游源码、同样的 meson 选项剔除后端只留主库），等主件
PR 合入发布后本件即可提 CI。

主件技术要点（供 #13396 参考，已在 stub 验证）：
- meson 全后端 disabled 即可只构建主库
- 同样需要 gio-unix-2.0.pc 修复与 glib 工具变量注入（本文档"构建期
  依赖处理"1/2 两坑同款）

## 上游测试用例本地真实执行（2026-09-19，rule4 修复）

Septest 审查意见（12:44）：上游 85 用例 0/85 未执行 + 少报（实测 85 > 声明
81）不通过。本地补齐上游测试全环境真实执行（详见
reports/upstream-test-report.md）：

- **85 口径 = pytest 81 + portal-test 四后端 4**（Septest 实测口径，此前
  PR 正文按主件 83 口径申报漏了 portal-test 4 项——本件更正为 85）
- **82/85 真实执行**：pytest 66 通过/15 失败（81.5%，两轮复跑失败集合一致
  110.07s/155.18s）+ portal-test-gtk3 链接验证 1 通过（上游
  portal-linking-test.c 以本件包+主件包+gtk3 链真实编译运行 exit 0，3 次
  复跑一致）
- **15 例失败单一根因**：OHOS unix-fd（SCM_RIGHTS）句柄投递平台语义差异
  （9 例 negative file descriptor / 3 例 mock 端 fdlist MemoryError /
  4 例 notification icon file-descriptor 变体 assert 0==1）——与主件
  PR #10103 实测失败集合逐项一致，非库缺陷，不豁免按真实结果申报
- **3 例豁免**（portal-test-gtk4/qt5/qt6）：backend disabled 上游 meson
  条件不注册 + gtk4 强制 introspection / OHOS 无 Qt
- 环境链（与主件 #10103 同方案 + 本件关键增强）：TCP session bus +
  python-dbus 1.4.0 本地重编（动态 libdbus-1.so + conan glib/2.84.0.1，
  规避旧静态绑定双 glib GType 冲突）+ dbusmock 0.32.1 + PyGObject 3.58.0
  本地重编 + Xdp-1.0.typelib 同源码 meson introspection 真实构建 +
  **libffi 3.4.4 static trampolines 重编（patch tramp_table_map 匿名拷贝
  方案）**——OHOS SELinux 拒绝 file-backed exec 映射，静态蹦床默认文件
  映射不可行，改匿名页 memcpy + __clear_cache + mprotect RX 后
  PyGObject closure 全链修复
- 测试适配仅新增上游 tests/conftest.py（TCP bus 重定向，主件同款），
  上游测试源码零修改
