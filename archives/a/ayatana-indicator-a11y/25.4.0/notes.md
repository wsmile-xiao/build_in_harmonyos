# ayatana-indicator-a11y 25.4.0 适配笔记（W0 依赖阻塞，未编译）

> **结论：本包无法在当前制品仓依赖条件下完成编译。** 上游 25.4.0（CMake
> 构建）在 CMake configure 阶段**硬性 REQUIRED** 两个未发布的依赖模块
> `accountsservice` 与 `xrandr`，且源码 `src/service.c` 无条件链接使用
> 这两个库的 API。按 W0/R36（依赖必须先发布再构建下游），本任务**停止适配**，
> 状态记为 `dependency_missing`。下方为完整证据与后续恢复路径。

## 软件简介
ayatana-indicator-a11y（Ayatana 系统辅助功能指示器）：读取用户无障碍
设置（屏幕阅读器 orca、放大镜、高对比度/主题、屏幕缩放/旋转），并通过
XRandR 与 AccountsService 应用/同步。产物为**守护进程二进制**
`ayatana-indicator-a11y-service`（非库），另有 GSettings schema、
D-Bus 接口 XML、polkit 策略、图标等数据文件。上游 25.4.0 为 **CMake** 构建
（init-build 误检为 autotools，已人工复核修正）。

## W0 依赖发布检查（适配前第一步）

### 可用的依赖（均已确认发布，二进制齐备）
| 上游 pkg-config 模块 | 需求写法 | Conan 包 | 状态 |
|---|---|---|---|
| glib-2.0 / gio-2.0 | `glib-2.0>=2.36 gio-2.0>=2.36` | `glib/2.84.0.1` | OK ohpcd 已发布，本地缓存有预编译二进制 |
| libayatana-common | `libayatana-common` | `ayatana-common/0.9.11` | OK 本地 conan 缓存 + `@ohpcd/stable`，可 require |
| x11 | `x11` | `libx11/1.8.13` | OK ohpcd 已发布 |

> 注：glib 只能用 `2.84.0.1`（与 ayatana-common/0.9.11 的 requires 一致）。
> 若直接 require `glib/2.84.0` 会与 ayatana-common 产生版本冲突
> （`Conflict between glib/2.84.0.1 and glib/2.84.0`）。

### 缺失的依赖（W0 阻塞点）
上游顶层 CMakeLists.txt 第 33 行：
```cmake
pkg_check_modules (SERVICE_DEPS REQUIRED glib-2.0>=2.36 gio-2.0>=2.36 accountsservice libayatana-common x11 xrandr)
```
两个 `REQUIRED` 模块 **在 ohpcd 制品仓、本地 conan 缓存、OHOS 系统库中均不存在**：

| 上游模块 | 用法（源码证据） | Conan/系统可用性 |
|---|---|---|
| `accountsservice` | `src/service.c` include `<act/act.h>`，调用 `act_user_manager_get_default()/act_user_manager_list_users()/act_user_get_user_name()/act_user_get_uid()`（用户会话检测，核心功能） | X ohpcd 无配方（`conan list "accountsservice/*" -r=ohpcd` -> 0）；本地缓存无；系统无 `libaccountsservice.so` / `act.h` |
| `xrandr` | `src/service.c` include `<X11/extensions/Xrandr.h>`，调用 `XRRGetScreenResources/XRRGetOutputPrimary/XRRSetCrtcConfig/XRRSetScreenSize` 等（屏幕缩放/旋转/DPI，核心功能） | X ohpcd 无 `libxrandr`（`conan list "*xrandr*" -r=ohpcd` -> 0；`conan download libxrandr/1.5.5 -r=ohpcd --only-recipe` -> not found）；`archives/l/libxrandr/1.5.5` 仅为 `status: built`（未发布）；系统无 `libXrandr.so` / `Xrandr.h` |

### 实测证据（cmake configure）
```text
-- Checking for modules 'glib-2.0>=2.36;gio-2.0>=2.36;accountsservice;libayatana-common;x11;xrandr'
--   No package 'accountsservice' found
--   No package 'xrandr' found
CMake Error at .../FindPkgConfig.cmake:639 (message):
  The following required packages were not found:
   - accountsservice
   - xrandr
```
可用依赖均正常解析（glib-2.0/gio-2.0/libayatana-common/x11 的 .pc 由
PkgConfigDeps 生成、`pkg-config --exists` 全 OK）——**唯一缺口就是这两个模块**。

## 判定
- 现象 -> status 对照表：`conan remote 上游包不存在/未发布，本地无法构建`
  -> **`dependency_missing`**
- 判定口径："换个网络正常的机器能否解决"——能（先发布 accountsservice 与
  libxrandr 即可）-> `dependency_missing`，非 `env_unsupported`。
- 任务描述的依赖清单（glib/2.84.0、libayatana-common、**gtk3**、libx11）
  与上游真实构建需求**不符**：gtk3 并非本包构建依赖（全树 grep 无 gtk+-3.0/
  gtk3/GTK3 构建引用，仅源码中 `"gtk-theme"` 字符串键）；真实硬依赖是
  accountsservice + xrandr（任务清单未列出）。

## 后续恢复路径（供 follow-up / 主控参考）
1. **先适配并发布缺失依赖**（R36，拓扑序）：
   - `libxrandr`：上游 1.5.5，依赖 libx11/libxext/libxrender（三者 ohpcd 已有）。
     `archives/l/libxrandr/1.5.5` 已有 `status: built` 配方可复用以发布。
   - `accountsservice`：上游（0.6.x/22.08.62 等），依赖 glib/gio、
     polkit、systemd（系统语义），需单独立项适配发布。
2. 两个依赖发布后，回本包 `finish --resume`：生成 conanfile.py（requires
   `glib/2.84.0.1 + ayatana-common/0.9.11 + libx11/1.8.13 + libxrandr/X +
   accountsservice/X`，CMake 配方），并沿用 Ayatana 系既有补丁模式（E544）：
   - `data/CMakeLists.txt` 的 `find_package(GSettings REQUIRED)` -> 新增
     `cmake/FindGSettings.cmake` shim（新建文件补丁首行必须 `--- /dev/null`）；
   - `po/CMakeLists.txt` 的 `find_package(Intltool REQUIRED)` -> po/ 可选化；
   - 产物为守护进程二进制 -> 需 `commands.json`（R38）。
3. 本任务未生成 conanfile.py/conandata.yml/test_package/patches——按 W0
   停止适配，避免产出无法验证的配方。

## 编译环境（探查用）
- 构建系统: cmake（init-build 误检 autotools，人工复核修正）
- 编译器: clang 15 (aarch64-linux-ohos)，Conan profile `ci/conan/profiles/ohos-aarch64`
- 依赖预编译验证：`conan install`（glib/2.84.0.1 + ayatana-common/0.9.11 +
  gtk/3.24.38 + libx11/1.8.13，`-pr:h/b=ohos-aarch64 -r=ohpcd`）-> 全 prebuilt 命中

## 注意事项
- `/tmp` 只读（E002）：中间产物一律用 `$HOME/tmp`。
- 上游 CMakeLists `PROJECT_VERSION` 仍为旧值 "24.4.2"（上游未随 tag 更新），
  以发布 tag 25.4.0 / NEWS / ChangeLog 为准（tarball 确为 25.4.0）。
---

**编译结束**: 2026-09-03（W0 阻塞）
**最终状态**: dependency_missing（accountsservice、libxrandr 未发布）

---

## 2026-09-17 主包适配（任务 #4 完成）

W0 阻塞解除：`accountsservice/26.27.3`、`libxrandr/1.5.5.1` 均已发布，
主包配方编写完成并通过静态校验：

- `conanfile.py`：package_type=application（守护进程），CMake 配方；
  requires `glib/2.84.0.1 + ayatana-common/0.9.11 + accountsservice/26.27.3 +
  libx11/6.4.0 + libxrandr/1.5.5.1`（libxrandr 实际发布为 1.5.5.1，位于
  libx11/6.4.0 track，随 track 使用 libx11/6.4.0 避免版本冲突）。
  glib-2.0/gio-2.0/gobject-2.0.pc 追加 `-lintl`（gi18n.h 的 g_libintl_* 符号）。
- 补丁 ×3（均已 dry-run 验证可干净应用）：
  - 0001 顶层 CMakeLists：`list(APPEND CMAKE_MODULE_PATH .../cmake)` +
    po/ 可选化（`find_package(Intltool QUIET)`，未找到跳过）。
  - 0002 新增 `cmake/FindGSettings.cmake` shim（新建文件补丁，含
    `add_schema()` 宏 + `GSETTINGS_SCHEMAS_INSTALL_DIR`，替代 Ubuntu
    cmake-extras）。
  - 0003 data/CMakeLists：硬编码 `/etc/xdg/autostart` →
    `${CMAKE_INSTALL_FULL_SYSCONFDIR}/xdg/autostart`（避免安装逃逸）。
- `test_package/`：daemon 类做安装产物完整性检查（libexec 下 ELF 守护进程
  + gschema + indicator 描述文件 + D-Bus 接口 XML + 图标），无需 D-Bus/X 会话。
- `commands.json`（软件级）：R38 要求，type=tool。
- manifest.yaml 状态置 archived（配方就绪，待构建验证后置 built/published）。

下一步：skill W3 本地构建验证（conan create 或 build_and_test.sh 分支内跑）。
