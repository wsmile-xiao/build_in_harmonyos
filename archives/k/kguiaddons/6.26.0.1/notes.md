# kguiaddons 6.26.0.1 适配笔记

## 版本概览

| 项目 | 6.26.0（已发布） | 6.26.0.1（本版） |
|---|---|---|
| 上游源码 URL / SHA256 | kguiaddons-6.26.0.tar.xz / `8375342f…3172` | 相同（同一 tarball） |
| patches | 无（`patches: {}`） | 无 |
| requires / tool_requires | qtbase/6.11.1、ecm/6.26.0 | 相同 |
| CMakeToolchain 变量 | 基线集合 | **+ 两个 soname 标志（本版唯一改动）** |

**为何递增版本号**：本版含**实质性适配修复**——注入 `CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG`
使产物真正带上 `DT_SONAME`（详见 Adaptations）。cnb.cool 制品仓不支持同版本多 recipe revision
并存（R37），故以 `.1` 后缀发布。本包同时是 `kio/6.26.0.1` 依赖闭包的一员。

## Adaptations

本版（`.1`）相对 6.26.0 的**唯一**改动：

- 在 `generate()` 的 `CMakeToolchain` 变量中注入
  `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG = -Wl,-soname,` 与
  `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG = -Wl,-soname,`。
  原因：OHOS 原生构建时 CMake 走 `Generic` 平台模块（上游无 `Platform/HarmonyOS`），
  `CMAKE_SHARED_LIBRARY_SONAME_*` 为空 → 链接器不会写入 `SONAME`，
  `VERSION`/`SOVERSION` 形同虚设；消费者据此把**构建机绝对路径**记入 `DT_NEEDED`，
  在干净缓存/CI worker 上必然加载失败。注入后产物获得 `DT_SONAME=libKF6GuiAddons.so.6`。

基线（6.26.0 已发布，零补丁）沿用：

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：绕过 KDE 平台白名单。
- `WITH_WAYLAND=OFF`、`WITH_X11=OFF`、`USE_DBUS=OFF`、`BUILD_GEO_SCHEME_HANDLER=OFF`、
  `BUILD_PYTHON_BINDINGS=OFF`：OHOS 无对应运行时/组件，关闭后零补丁通过。
- `BUILD_TESTING=ON`：在 conan create 内执行上游 CTest autotests。
- `generate()` 手工注入 `ECM_MODULE_PATH` 与 qtbase 的 `lib/cmake` 路径
  （qtbase 为 `cmake_find_mode=none`，CMakeDeps 不生成该路径）。

## 上游测试执行

`BUILD_TESTING=ON` 下上游 CTest 全量 8/8 通过（无排除项）：

| # | 测试 | 结果 | 耗时 |
|---|---|---|---|
| 1 | kwordwraptest | Passed | 0.05s |
| 2 | kcolorutilstest | Passed | 0.19s |
| 3 | kiconutilstest | Passed | 0.05s |
| 4 | kcursorsavertest | Passed | 0.04s |
| 5 | kkeysequencerecordertest | Passed | 19.49s |
| 6 | kurlhandlertest | Passed | 0.04s |
| 7 | kcountryflagemojiiconenginetest | Passed | 0.06s |
| 8 | kgeourihandlertest | Passed | 0.03s |

`100% tests passed, 0 tests failed out of 8`（Total Test time 19.96 sec）。

## Verification

- 强制重建：`conan create . -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=kguiaddons/* --build=missing`
  → rc=0（日志 `ymdsymds/tmpdir/gui-create.log`）。
- 包 id：`57ffd8c720a5bfee7e8827990cd6550a49181c1b`；包目录 `.conan2/p/b/kguiafc1fd78061523/p`。
- 产物：`lib/libKF6GuiAddons.so{,.6,.6.26.0}`、`include/KF6/KGuiAddons/*`、`share/`。
- `readelf -d`：
  `SONAME Library soname: [libKF6GuiAddons.so.6]`；
  `NEEDED`：`libQt6Gui.so.6`、`libQt6Core.so.6`、`libc++_shared.so`、`libc.so`（无构建机绝对路径）。
- 消费者测试：`test_package` 1/1（`kguiaddons test_package: all assertions passed`）。
- 本包为纯库（产物无 `bin/`），不产生新的命令行声明；软件级 `commands.json` 由 main 既有版本维护。

## 对话记录

### 对话 #1 — 2026-09-30

- 评估（编译前）：`.1` 配方 vs 已发布 `6.26.0` 逐文件比对，差异 11 行 = 版本号字符串 +
  soname 注入块（含注释）。与 kcodecs/6.26.0.1 的"纯版本对齐无行为改动"情形不同，
  本包**确有适配修复**，符合 R37 版本后缀语义。
- 制品仓核验：`kguiaddons/6.26.0` 已发布（recipe revision `3ea0ad586e28811721bcf426b0b36643`，
  2026-09-09）；`6.26.0.1` 探测时远端返回 `system acceleration policy not enabled`（策略错误
  而非干净 404），结论未定论，待 CI/上传阶段复核。
- 建仓：worktree `.wt-kguiaddons`，分支 `feat/kguiaddons-6.26.0.1`，基线 `origin/main 60ed502492`；
  配方 = main 的 `6.26.0` 目录复制后施加版本号与 soname 两处改动（与闭包工作区 `.wt-kio`
  的 `.1` 配方逐字节一致）。
- 构建：强制重建 rc=0，上游 CTest 8/8（19.96s），消费者测试 1/1。
---

**编译结束**: 2026-09-30 15:06
**最终状态**: built
