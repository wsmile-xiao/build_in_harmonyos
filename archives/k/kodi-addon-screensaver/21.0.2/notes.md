# kodi-addon-screensaver 21.0.2 适配笔记

## 源码
- 上游: xbmc/screensaver.asteroids（Kodi 屏保插件 "Asteroids"）
- tag: `21.0.2-Omega`（tag commit 7345b182f9b689bcf4c95db50919bc2f8f874cf7）
- URL: https://github.com/xbmc/screensaver.asteroids/archive/refs/tags/21.0.2-Omega.tar.gz
  （conandata 按 gh-proxy 优先双 URL 列表）
- SHA256: 468527220845a411af4dd021a907c6449327015fb848e61adfb46b47edde331a（实测）
- SDK: Kodi 插件 SDK 头取自 xbmc 21.3-Omega 发布 tarball（kodi-tools/21.3 同源）
  - https://github.com/xbmc/xbmc/archive/refs/tags/21.3-Omega.tar.gz
  - SHA256: a60afcb556e4a00cb19fc35b7e77758107c9a8096c6ce9b66af5f92396be31aa
    （与 kodi-tools/21.3 conandata 记录值一致；只选择性提取
    `xbmc/addons/kodi-dev-kit/include` 子树，约 2.8MB，不展开整个 xbmc 树）

## license 复核
- LICENSE.md：GPLv2 全文（"The GNU General Public License, Version 2"）
- `screensaver.asteroids/addon.xml.in`：`<license>GPL-2.0-or-later</license>`
- 配方 license 字段：`GPL-2.0-or-later`（与 addon.xml 一致；kodi-tools/21.3 同措辞）

## 依赖分析（W0）
- 上游 CMakeLists：`find_package(Kodi REQUIRED)` + `build_addon()` 宏 +
  自带 FindOpenGl/FindOpenGLES/Findglm.cmake（无 FindKodi.cmake，Kodi 模块
  随 kodi-addon-dev 发行）
- `APP_RENDER_SYSTEM=gl|gles` 双路径；OHOS PC aarch64 走 GLES（系统
  GLESv3/libEGL，实测设备 clang 默认即可编译链接 GLES3/EGL 头与库）
- glm：上游 depends 固定 0.9.9.4；registry 提供 glm/0.9.9.8 与 1.0.3，
  取同 0.9.9 系的 0.9.9.8（源码仅用 `glm/glm.hpp`、`glm/gtc/type_ptr.hpp`）
- kodi-addon-dev SDK 在 ohpcd registry 不存在（R36，同 kodi-platform 先例）
- 源码包含面（决定 SDK 头集合）：`kodi/addon-instance/Screensaver.h`、
  `kodi/gui/gl/GL.h`、`kodi/gui/gl/Shader.h` + glm；`<d3d11.h>` 位于
  `#ifndef WIN32` 的 else 分支，OHOS 不会触及

## 适配方案

### 1. 配方自带构建入口（recipe-cmake/ 子目录，kodi-platform 三陷阱规避）
上游 `find_package(Kodi)+build_addon()` 需要 kodi-addon-dev（registry 无）。
按 kodi-platform/20250416 先例：构建入口放 `recipe-cmake/`（上游 tarball 无
此目录，规避 config_source 覆盖陷阱），主配方显式 `generators = "CMakeDeps"`
（第二陷阱），test_package 消费 find_package 走 CMakeDeps（第三陷阱：间接
依赖 INCLUDE_DIRS 为空——本配方 test_package 只 dlopen 产物，无传递依赖，
不受影响）。

recipe-cmake/CMakeLists.txt 复刻 build_addon 的关键语义：
- `add_library(MODULE)` + `PREFIX ""` → 产物名 `screensaver.asteroids.so`
  （addon.xml `library_filename` 期望的准确文件名）
- `HAS_GLES=3`（上游 FindOpenGLES 找到 GLES3 头时置 -DHAS_GLES=3；同时选择
  SDK GL.h 的 GLES3 分支与 `GL_TYPE_STRING "GLES"` shader 目录）
- 链接系统 `GLESv3`、`EGL`（OHOS GLES 路径；编译器默认搜索路径可用）
- cxx_std_17（Kodi 21 插件 SDK 要求）
- 上游源码零修改，无 patch（conandata `patches: {}`）

### 2. Kodi SDK 头的选择性提取
conandata `sources.sdk` 记录 xbmc tarball；source() 用 download()+tarfile
只解出 `kodi-dev-kit/include` 并重排为 `kodi-sdk-include/`（整个 xbmc 树
解压达数百 MB，无必要）。下载失败按 URL 列表逐个回退，sha256 全程校验。

### 3. versions.h 宏策略
上游 build_addon 会扫描插件源码 include 行生成 `ADDON_*_USED` 宏并定义
`BUILD_KODI_ADDON`。该浅文本扫描实际检不出 screensaver 实例 API（其
DEPENDS 头是 `c-api/addon-instance/screensaver.h`，而源码直接包含的是
`addon-instance/Screensaver.h`）；若定义 `BUILD_KODI_ADDON` 而缺对应 USED
宏，versions.h 的 GetAddonVersion/GetTypeVersion switch 对 screensaver 实例
类型将无 case（落空）。本配方选择**不定义** `BUILD_KODI_ADDON`：versions.h
编译完整版本表，对宿主任何实例类型查询都返回正确版本字符串（相当于 Kodi
本体的编译路径），test_package 运行时验证 `GetTypeVersion(108)=="2.2.0"`。

### 4. 安装布局
- `lib/screensaver.asteroids.so`（Kodi 宿主按 addon.xml 部署加载的模块）
- `licenses/LICENSE.md`
- addon.xml 与 resources 属 Kodi 宿主运行时部署面，由宿主集成步骤落位，
  本包不重复打包

## 上游测试核查（NO_UPSTREAM_TESTS discovery）

```json
{
  "conclusion": "NO_UPSTREAM_TESTS",
  "discovery_status": "EVIDENCE_COMPLETE",
  "upstream": "xbmc/screensaver.asteroids tag 21.0.2-Omega",
  "checks": [
    {"check": "tarball tree has no test directories or test files",
     "command": "find . -type d -iname '*test*' -o -type f -iname '*test*'",
     "result": "no matches in 21.0.2-Omega tree",
     "evidence_paths": ["21.0.2-Omega tarball (full tree)"]},
    {"check": "no CMake test registration",
     "command": "grep -nE 'enable_testing|add_test|\\.ctest' CMakeLists.txt",
     "result": "no matches; CMakeLists only declares sources and build_addon()",
     "evidence_paths": ["CMakeLists.txt"]},
    {"check": "upstream CI is build-only",
     "command": "read .github/workflows/build.yml .travis.yml azure-pipelines.yml Jenkinsfile",
     "result": "build.yml = 'Build and run tests' but steps are cmake configure + make (Debian package build) only; travis/azure/Jenkins build matrix only",
     "evidence_paths": [".github/workflows/build.yml", ".travis.yml", "azure-pipelines.yml", "Jenkinsfile"]},
    {"check": "no test framework sources or fixtures",
     "command": "tree inspection of src/ and resources/",
     "result": "src/ holds 5 translation units + headers of the screensaver itself; no test runner, no fixtures, no language test bindings",
     "evidence_paths": ["src/", "resources/"]}
  ],
  "official_test_count": 0,
  "evidence_paths": [
    "https://github.com/xbmc/screensaver.asteroids/tree/21.0.2-Omega",
    "21.0.2-Omega source tarball (sha256 468527220845a411af4dd021a907c6449327015fb848e61adfb46b47edde331a)"
  ],
  "conclusion_rationale": "上游 0 个官方测试，N=0 口径成立；test_package 按仓内惯例补消费者侧真实检查（dlopen + 入口符号 + 版本 API 断言）"
}
```

## test_package（消费者侧）
`test_screensaver_asteroids`：dlopen 打包产物 `screensaver.asteroids.so` →
dlsym 三个 Kodi 二进制插件入口（ADDON_Create / ADDON_GetTypeVersion /
ADDON_GetTypeMinVersion，来自 kodi/AddonBase.h 的 ADDON 宏）→ 实际调用
`ADDON_GetTypeVersion(108)`/`ADDON_GetTypeMinVersion(108)` 断言 screensaver
实例 API 版本 "2.2.0"（xbmc 21.3-Omega SDK kodi/versions.h）。5 项断言。
screensaver 无独立运行入口、渲染需显示与宿主，headless CI 只能验证到
加载/符号/版本 API 层。

## 本地验证（G2，conan create + test_package）
- conan create（ohos-aarch64 host/build profile 显式传入）：PASS
- 模块编译：`Linking CXX shared module screensaver.asteroids.so`
- package()：Packaged 1 '.so' file: screensaver.asteroids.so + LICENSE.md
- test_package：编译链接 PASS，运行 5/5 断言全过（dlopen 产物、三个入口
  符号、screensaver 实例 API 版本/最小版本 "2.2.0"）
- 权威 CI（ci/conan/build_and_test.sh）另行运行，结果见 run 报告

## 风险
- 渲染正确性无法 headless 验证（需 Kodi 宿主 + 显示）；本包保证模块可加载、
  入口与 API 版本契约正确
- GLES shader 运行路径（resources/shaders/GLES）由宿主部署后生效
- device FS 大小写不敏感导致的 worktree 幽灵 dirty 条目与本包无关

---

**适配日期**: 2026-09-22
**状态**: 见版本 manifest.yaml
