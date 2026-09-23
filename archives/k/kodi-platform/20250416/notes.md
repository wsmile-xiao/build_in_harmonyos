# kodi-platform 20250416 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-09-12
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18）
- 状态: built（W3 本地 conan create + test_package 全过，CI upload 待 PR 合并）

## 源码
- 上游: xbmc/kodi-platform（tag `kodiplatform-20250416`，注意 tag 前缀是
  `kodiplatform-` 而非 `kodi-platform-`）
- URL: https://github.com/xbmc/kodi-platform/archive/refs/tags/kodiplatform-20250416.tar.gz
- SHA256: e559715b37b91e219ea2bb72cff0d0b29cf08386685fd12328520a294bb17b57（实测）

## 依赖分析（W0）
- 上游 CMakeLists: `find_package(Kodi REQUIRED)` + `find_package(TinyXML REQUIRED)` +
  `find_package(Threads REQUIRED)` + `find_package(p8-platform REQUIRED)`
- 源码事实核查：全部源码只有 `src/util/XMLUtils.cpp` 一个 TU，只 include
  `tinyxml.h` 与 `<p8-platform/util/StringUtils.h>`——**不使用任何 Kodi 头文件**。
  `find_package(Kodi)` 仅提供 APP_VERSION_MAJOR/MINOR（库版本号）与
  KODI_INCLUDE_DIR（include 路径传给 include_directories，但源码不用）
- Kodi 本体（kodi-addon-dev SDK）在 ohpcd registry 不存在 → 不可依赖（R36）
- 实测在仓: tinyxml/2.6.2 ✅、p8-platform/2.1.0 ✅（conan download --only-recipe 验证）

## 适配方案

### 1. 配方自带构建入口（recipe-cmake/ 子目录）
上游 CMakeLists 的 `find_package(Kodi REQUIRED)` 需要 kodi-addon-dev 的
FindKodi.cmake / KodiConfig.cmake（registry 无 kodi 包）。处理方式与仓库
tinyxml/2.6.2 先例一致：配方自带最小 CMakeLists.txt 构建**同样的上游源码**
（src/util/XMLUtils.cpp），依赖改走 Conan CMakeDeps（tinyxml::tinyxml +
p8-platform::p8-platform target）。库版本号 21.2 沿用上游语义（取自 Kodi 21.2
"Omega" 系列——kodiplatform-20250416 tag 时代的 kodi 稳定版）。

**关键陷阱（踩坑记录）**：Conan 2 的 `config_source()` 流程是先把
exports_sources merge 进 source 目录、**再**运行 source()——上游 tarball 解压
会用自带的 CMakeLists.txt 覆盖同名导出文件（实测复现）。解法：把构建入口放
`recipe-cmake/` 子目录（上游 tarball 无此目录，不可能被覆盖），source() 里
从 recipe_folder 复制出来，build() 用 `cmake.configure(build_script_folder=
"recipe-cmake")`。

**第二个陷阱**：主配方必须声明 `generators = "CMakeDeps"`（CMakeToolchain 由
ConanTools 自动，但 CMakeDeps 的 *-config.cmake 生成文件只有显式声明
generators 才产出——缺失时 find_package(tinyxml CONFIG REQUIRED) 直接失败）。

**第三个陷阱（OHOS conan 2.29 特性）**：test_package 对**间接依赖**
（tested_reference 的 requires）生成的 CMakeDeps data 中 INCLUDE_DIRS 为空
（实测：tinyxml 与 p8-platform 的 `<pkg>_INCLUDE_DIRS_RELEASE` 均空）。
test_package 必须显式 `self.requires("tinyxml/2.6.2")` 与
`self.requires("p8-platform/2.1.0")`（仓库 accel-config/4.1.9 等先例），
XMLUtils.h 直接 include tinyxml.h 也确实需要其 include 路径。

### 2. 上游源码零修改
无 patch。conandata.yml `patches: {}`。

### 3. 安装布局（与上游一致）
- `include/kodi/util/XMLUtils.h`（下游 Kodi PVR add-on `#include <kodi/util/XMLUtils.h>` 不变）
- `lib/libkodiplatform.a`（默认静态；shared 选项可用）
- `lib/pkgconfig/kodiplatform.pc`（上游同名的简化版）

## Conan 配方
- package_info: cmake_file_name=`kodiplatform`（对齐上游 config-mode 文件名
  kodiplatform-config.cmake），cmake_target_name=`kodiplatform::kodiplatform`，
  requires 传递 tinyxml/p8-platform
- R26: 非系统同名库，默认静态（libkodiplatform.a），无 /lib 污染风险

## 验证结果（W3，本地实测）
- conan create（ohos-aarch64 profile）: PASS
- test_package 编译链接: PASS
- test_package 运行 18/18 断言全过（Set/Get 往返: int/string/bool/float/hex/
  path、范围钳制 GetInt(min,max)、HasChild、GetEncoding 空文档、
  HasUTF8Declaration 正反例）
- 产物: libkodiplatform.a + include/kodi/util/XMLUtils.h + kodiplatform.pc

## 上游测试
上游 kodiplatform-20250416 无任何测试注册（无 enable_testing/add_test、无
test/ 目录、Debian 包也无测试），N=0。test_package 补全消费者测试（18 断言）。

## 解锁关系
本包是 kodi-pvr（平台任务 #213 积压件）的前置依赖——kodi-pvr 的 add-on 构建需要
kodiplatform 提供 XMLUtils。

---

**编译结束**: 2026-09-12
**最终状态**: built
