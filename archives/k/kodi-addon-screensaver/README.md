# kodi-addon-screensaver

Kodi 屏保插件 "Asteroids"（上游项目 id `screensaver.asteroids`，xbmc/
screensaver.asteroids）的 OHOS 移植。Kodi 21 "Omega" 系二进制屏保插件：
C++/OpenGL ES 渲染，在 Kodi GUI 内部以模块（`screensaver.asteroids.so`）
形式被宿主加载，无独立运行入口。

## 版本

| 版本 | 上游 tag | 状态 | 说明 |
|---|---|---|---|
| 21.0.2 | 21.0.2-Omega | built | GLES 渲染路径，Kodi SDK 头取自 xbmc 21.3-Omega |

## OHOS 适配要点

1. 上游 CMake 需要 `find_package(Kodi)` + `build_addon()`（kodi-addon-dev
   发行内容，registry 无 kodi 包）。配方自带 `recipe-cmake/` 构建入口，按
   上游 `APP_RENDER_SYSTEM=gles` 路径构建**上游原样源码**：模块目标
   `screensaver.asteroids`（PREFIX 空，产物名 `screensaver.asteroids.so`），
   `HAS_GLES=3`，链接系统 `GLESv3`/`EGL`。
2. Kodi 插件 SDK 头（`kodi/`）从 xbmc 21.3-Omega 发布 tarball 的
   `xbmc/addons/kodi-dev-kit/include` 子树选择性提取（conandata
   `sources.sdk`，双 URL + sha256 固定）。
3. glm 依赖：上游 `depends` 固定 0.9.9.4，registry 提供 0.9.9.8（同 0.9.9
   系），插件只用头文件级 API。
4. 上游无测试套件（见 `21.0.2/notes.md` 的 NO_UPSTREAM_TESTS 记录）；
   test_package 做真实消费者检查：dlopen 打包模块 + dlsym 三个 Kodi 二进制
   插件入口符号 + 运行 `ADDON_GetTypeVersion/MinVersion` 校验 screensaver
   实例 API 版本。

## 已知限制

- 无显示/宿主环境下无法验证实际渲染（screensaver 在 Kodi GUI 内运行）；
  Kodi 宿主移植属后续任务，本包提供可加载的模块产物。
