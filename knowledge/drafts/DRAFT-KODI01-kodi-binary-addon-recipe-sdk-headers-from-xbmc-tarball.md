# DRAFT-KODI01-kodi-binary-addon-recipe-sdk-headers-from-xbmc-tarball：宿主 SDK 开发包缺失使 find_package 失败时，二进制插件类库应在配方层自备构建入口复刻上游宏语义，并从上游发布 tarball 选择性提取 SDK 头

> Contributor: why6666666 | Status: Draft | Updated: 2026-09-22
> Source: kodi-addon-screensaver 21.0.2（screensaver.asteroids，tag 21.0.2-Omega）适配；kodi-platform/20250416 与 kodi-tools/21.3 为同型先例
> 对应：`knowledge/drafts/DRAFT-KODI01-kodi-binary-addon-recipe-sdk-headers-from-xbmc-tarball.kv`
> 最终编号 Exxx 由知识库主编确认

## 现象

Kodi 系二进制插件（xbmc 生态 `xbmc/<class>.<app>` 仓：screensaver.\*、inputstream.\*、pvr.\*、visualization.\*）在只有 Conan 化依赖、无宿主 SDK 安装的环境按上游方式构建时，configure 阶段直接失败：

```console
CMake Error at CMakeLists.txt:6 (find_package):
  Could not find a package configuration file provided by "Kodi" with any of
  the following names: KodiConfig.cmake, kodi-config.cmake
```

上游 CMakeLists 是标准的"宿主 SDK 式"写法：

```cmake
find_package(Kodi REQUIRED)
find_package(glm REQUIRED)
build_addon(screensaver.asteroids ASTEROIDS DEPLIBS)
```

在装了 Kodi/kodi-addon-dev 的机器上一切正常；在 ohpcd registry（无 kodi 包）+ 无系统安装的构建机上必然失败。

## 根因（因果链）

1. **工具实现证据**：`FindKodi.cmake`/`KodiConfig.cmake` 与 `build_addon()` 宏（xbmc 源树 `cmake/scripts/common/AddonHelpers.cmake`）随 kodi-addon-dev/Kodi 本体发行，**不在插件仓内**——插件仓只自带 `FindOpenGl/FindOpenGLES/Findglm` 这类次级模块。
2. **触发命令**：上游插件 CMakeLists 的 `find_package(Kodi REQUIRED)`。
3. **失败点**：目标环境无 kodi-addon-dev → CMake configure 报 `Could NOT find Kodi` → 构建不可进行。
4. **归类**：宿主 SDK 安装布局假设被打破 → 依赖闭包断裂。**非 OHOS 专有**，任何"只有 Conan 化环境、无宿主 SDK 包管理"的构建面同构复现。

**第二层机理（本库新贡献）**：`build_addon()` 通过对插件源码 include 行的**浅文本扫描**生成 `ADDON_DEPENDS` 并定义 `ADDON_*_USED` 宏。扫描用的 DEPENDS 头是 c-api 相对路径（如 `c-api/addon-instance/screensaver.h`），而源码直接 include 的是对应 C++ 头（`addon-instance/Screensaver.h`）——**实例 API 的 USED 宏实际检不出来**。若配方照直觉定义 `BUILD_KODI_ADDON` 而缺 USED 宏，SDK 头 `kodi/versions.h` 的版本 switch 对该实例类型缺 case，`ADDON_GetTypeVersion()` 返回空/未定义——**编译期无报错，问题静默推迟到宿主运行期**。

## 方案（配方层桥接，上游源码零修改）

**主方案：recipe-owned build entry + selective SDK extract**

1. conandata `sources` 拆 `addon`+`sdk` 两个子键；sdk 指向 xbmc 发布 tarball（gh-proxy 优先双 URL + sha256 固定），`source()` 用 `download()+tarfile` 只提取 `xbmc/addons/kodi-dev-kit/include` 子树（约 2.8MB；整树解压数百 MB，无必要）；
2. 构建入口放 `recipe-cmake/` 子目录、经 `build_script_folder` 消费，复刻 `build_addon()` 关键语义：`MODULE` 目标 + `PREFIX ""`（产物名 `<addon id>.so`，即 addon.xml `library_filename` 期望的文件名）、`HAS_GLES=3`（GLES 渲染路径，同时选择 SDK GL.h 的 GLES3 分支与 `GL_TYPE_STRING "GLES"` shader 目录）、`cxx_std_17`、链接系统 `GLESv3`/`EGL`；
3. 三陷阱规避（kodi-platform/20250416 实测记录）：exports_sources **先 merge 后 source()** → 入口放上游 tarball 不存在的子目录；主配方显式 `generators = "CMakeDeps"`；test_package 对间接依赖 `INCLUDE_DIRS` 为空 → 显式 requires；
4. **不定义** `BUILD_KODI_ADDON`/`ADDON_*_USED`：让 `versions.h` 编译完整版本表，宿主查询任何实例类型都返回正确版本串（`test_package` 运行时断言实证）。

**退路（诚实权衡）**

- `extract-full-xbmc-tree`：tarfile 选择性提取不可用时，`get(strip_root=True)` 整树解压、SDK include 直连深层路径——磁盘数百 MB + 解压时间换实现简单，语义不变，仅作退路；
- `system-kodi-addon-dev-assumption`：环境恰有 kodi-addon-dev 时走上游原生流程——把 CI 可移植性押在环境假设上，registry/CI 不保证提供；不得为走这条路在设备上手工散布 SDK 头（见禁止项）。

**禁止项**

- **禁止凭直觉定义 `BUILD_KODI_ADDON`/`ADDON_*_USED`**：浅文本扫描检不出实例 API 的 USED 宏，缺宏 → `versions.h` 版本 switch 缺 case → `ADDON_GetTypeVersion(<实例类型>)` 返回空/未定义，编译期零报错、宿主运行期才暴露；
- **禁止把 SDK 头拷进系统 include / 全局软链**："让 find_package 通过"的假修，掩盖 kodi-addon-dev 缺失真因并污染系统路径（P012 同向）。

## 判别（三行定位）

```sh
# 1) 上游是否为宿主 SDK 式构建
grep -nE 'find_package\((Kodi|<Host>) REQUIRED\)|build_addon\(' CMakeLists.txt

# 2) 错误签名是否命中（无宿主 SDK 环境 configure）
cmake -S . -B kprobe-build 2>&1 | tail -3

# 3) SDK 头是否确实随宿主发布 tarball 发行（桥接来源证据）
tar tzf xbmc.tar.gz | grep 'kodi-dev-kit/include/kodi/versions.h'
```

## 验证（真实证据）

实例库 kodi-addon-screensaver/21.0.2（screensaver.asteroids 21.0.2-Omega）：

- 主方案配方本地 `conan create`（ohos-aarch64 host/build profile 显式传入）：模块链接 `screensaver.asteroids.so`、test_package 5/5 断言全过（dlopen 打包产物、`ADDON_Create`/`ADDON_GetTypeVersion`/`ADDON_GetTypeMinVersion` 三个入口可解析、`ADDON_GetTypeVersion(108)=="2.2.0"`）；
- 权威 CI（`ci/conan/build_and_test.sh`，同 profile）全绿：L0 pass / L1 pass（test_package executed）/ L4 pass / L5 pass（lib/ has content），Summary 1/1；**L1e 破坏性负向验证确认 test 真实依赖被测包**（sabotage lib/ 后重跑失败）；
- 阻塞面：本 run 配方设计即绕开，无本库自身 `find_package(Kodi)` 失败日志；同签名先例见 `archives/k/kodi-platform/20250416/notes.md`（"Kodi 本体（kodi-addon-dev SDK）在 ohpcd registry 不存在 → 不可依赖（R36）"）。自包含阻塞面探针见 .kv `verification_cmd` (a)，任何无 Kodi 安装的构建机可复现。

## 适用边界

- **触发面**：任何"宿主程序加载的插件"形态、上游构建依赖宿主 SDK 开发包（`find_package(<Host> REQUIRED)` + 宿主宏）的项目，在无宿主 SDK 的 Conan 化环境构建时命中；
- **非 OHOS 专有**：机理与平台无关，OHOS 只是本条实证环境；
- **反例**：宿主 SDK 在 registry/系统确实可得 → 走上游原生流程即可，不必桥接；`find_package` 失败但根因是次级依赖（glm/OpenGLES）缺失 → 是依赖闭包问题而非本模式。

## 关系

- `E345`（可加载模块/插件 dlopen 运行时验证族）、`E442`（宿主加载插件私有 ABI/未解析宿主符号族）：本条 test_package 的 dlopen+入口符号验证直接复用其思想；
- `E322`/`E323`/`E451`/`E473`（conan-cmake 消费/生成器模式族）：三陷阱规避与之同域；
- `E150`（上游 tarball/submodule 缺失目录桥接族）：选择性提取 SDK 头与之同向；
- 原则：P012（静态库优先/系统库冲突防护——模块部署不污染系统路径）、P013（平台限制降级而非绕过——headless 无法验证渲染，test_package 诚实收缩到契约层）。

## 查重（Curator 确认审计）

检索范围：`knowledge/graph/index.tsv`（base 48d9cee6，766 行）、`knowledge/graph/` 全部 E 条目、`knowledge/drafts/` 全列表、经验仓 `ophs_ci_review` 九分类全树。

- 检索词：`kodi|addon|screensaver|dev-kit|build_addon`、`dlopen|find_package|recipe-cmake`，经验仓 `kodi`/`screensaver`；
- 命中：index.tsv 无任何 Kodi 专属条目（E150/E195/E204/E335 仅 tarball 字样噪声命中）；drafts 无 kodi/screensaver 文件；经验仓 0 命中；
- 相近族差异：E345/E442 覆盖"dlopen 契约验证/宿主 ABI"，不覆盖"无宿主 SDK 包时自备 SDK 头 + 复刻 build_addon 语义 + versions.h 宏策略"任一要素；E322/E323/E451/E473 为 conan-cmake 消费模式，同域不同题；
- **结论：查重无覆盖成立**——Kodi 插件生态在 ohpcd 的首个通用配方模式条目，kodi-pvr 等同构积压件直接受益。
