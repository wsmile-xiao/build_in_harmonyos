# kodi-game-libretro

Kodi 游戏客户端插件 "Libretro Compatibility"（上游项目 id `game.libretro`，
kodi-game/game.libretro）的 OHOS 移植。Kodi 21 "Omega" 系二进制插件：作为
`kodi.gameclient` 扩展点被 Kodi 宿主以模块（`game.libretro.so`）形式加载，
运行期 dlopen libretro core，把 core 包装成 Kodi Game API 游戏插件，无独立
运行入口。

## 版本

| 版本 | 上游 tag | 状态 | 说明 |
|---|---|---|---|
| 21.0.10 | 21.0.10-Omega | built | vendored libretro-common/rcheevos，Kodi SDK 头取自 xbmc 21.3-Omega |

## OHOS 适配要点

1. 上游 CMake 需要 `find_package(Kodi)` + `build_addon()`（kodi-addon-dev
   发行内容，registry 无 kodi 包）。配方自带 `recipe-cmake/` 构建入口构建
   **上游原样源码**：模块目标 `game.libretro`（PREFIX 空，产物名
   `game.libretro.so`），上游 34 个 .cpp 源清单，链接 tinyxml + vendored
   rcheevos。
2. Kodi 插件 SDK 头（`kodi/`）从 xbmc 21.3-Omega 发布 tarball 的
   `xbmc/addons/kodi-dev-kit/include` 子树选择性提取（conandata
   `sources.sdk`，双 URL + sha256 固定）。game client 实例 API：
   `ADDON_INSTANCE_GAME=104`，版本 "3.0.2"（min "3.0.0"）。
3. vendored 依赖（registry 无包，按上游 `depends/common/` pin）：
   - libretro-common @ 50c15a88（header-only，源码以
     `"libretro-common/<header>.h"` 形式包含 → 重排为
     `libretro-common-include/libretro-common/`）
   - rcheevos @ v9.2.0（C 静态库，上游源清单 + `RC_DISABLE_LUA` + PIC，
     源码以 `"rcheevos/<header>.h"` 形式包含 → 公共头镜像为
     `rcheevos-include/rcheevos/`）
4. tinyxml：上游 pin 2.6.2 系（TIXML_USE_STL）→ registry `tinyxml/2.6.2`
   （`tinyxml::tinyxml`，with_stl 默认开）。
5. 上游无测试套件（见 `21.0.10/notes.md` 的 NO_UPSTREAM_TESTS 记录）；
   test_package 做真实消费者检查：dlopen 打包模块 + dlsym 三个 Kodi 二进制
   插件入口符号 + 运行 `ADDON_GetTypeVersion/MinVersion` 校验 game client
   实例 API 版本。

## 已知限制

- 实际游戏运行需 Kodi 宿主 + libretro core（core 由本插件运行期 dlopen）；
  headless CI 只验证模块加载、入口符号与版本 API 契约。Kodi 宿主移植属后续
  任务，本包提供可加载的模块产物。
- 成就（Cheevos）运行期联网行为不在 CI 覆盖面。
