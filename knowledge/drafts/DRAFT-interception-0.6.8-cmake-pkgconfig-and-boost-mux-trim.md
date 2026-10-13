# CMake 裸名链接改 pkg_check_modules + Boost 缺组件时裁剪目标(interception 0.6.8 载体)

- **草稿 ID**: DRAFT-interception-0.6.8-cmake-pkgconfig-and-boost-mux-trim
- **来源**: interception/0.6.8 适配(贡献者页直接领取任务,PR 同分支提交)
- **分类**: cmake / cross-build / conan / boost
- **状态**: 随 PR 提交(feat/interception-0.6.8,待 CI/审核)

## 问题 / 错误签名

- 上游 `target_link_libraries(udevmon evdev udev yaml-cpp)` 用裸 `-l` 名:
  conan 依赖库不在交叉工具链默认搜索路径,链接期
  `cannot find -ludev/-lyaml-cpp` 或链到宿主库;
- `find_package(Boost REQUIRED)` + `add_executable(mux …)`:
  mux 需 Boost.Interprocess,而仓库 boost 配方(1.85/1.91,为 Redex 定制)
  组件集仅 filesystem/iostreams/program_options/regex/thread,
  **interprocess 未被覆盖** → 配置期直接失败;
- `cmake_minimum_required(VERSION 3.0)`:现代 CMake 对 <3.5 声明报错。

## 根因

1. 裸 `-l` 名的解析依赖宿主链接搜索路径;conan 的 CMakeDeps 产出的是
   CMake target,不会为裸名注入 -L;
2. 上游把可选组件(mux)硬编进主 CMakeLists 且对 Boost 用 REQUIRED;
3. cmake_minimum 3.0 低于现代 CMake 的兼容下限。

## 最小修复方案(单补丁 0001-cmake-ohos-deps.patch)

1. `cmake_minimum_required(VERSION 3.0)` → `3.10`;
2. `pkg_check_modules(UDEV REQUIRED udev)`、`pkg_check_modules(YAMLCPP
   REQUIRED yaml-cpp)`,三工具的 target_link_libraries 改
   `${LIBEVDEV_LIBRARIES} ${UDEV_LIBRARIES} ${YAMLCPP_LIBRARIES}`;
3. 删除 mux 的 add_executable/链接/install 四行与 find_package(Boost)。

## 备选方案

- 为 boost 配方追加 interprocess 组件(需要平台重新编译发布 boost,
  周期长、影响面大,不现实);
- 保留 mux 并用 ExternalProject 自带 yaml-cpp/boost 源码(引入网络依赖,
  违反 R 系列离线原则)。

## 实际验证结果

- 补丁由 pristine 副本 git diff --no-index 生成(行号精确);
- 源码 musl 风险 grep 干净(无 program_invocation_short_name/rindex/
  strcasestr/get_current_dir_name);
- 构建与 test_package(三工具 -h 真实执行)由 CI conan create 完成,
  结果见 PR。

## 适用范围

- CMake 工程 target_link_libraries 使用裸库名的交叉构建;
- 对 REQUIRED 的外部大依赖(Boost 等)在上游可选目标中出现的场景;
- 与本仓既有知识互补:libinput/consolation 是 autotools+裸链接到
  pkg-config 的先例,本条覆盖 cmake 分支。

## 非适用边界

- 已用 find_package + target 的现代工程无需此模式;
- Boost 组件已被仓库配方覆盖时,优先 require 而非裁剪目标;
- mux 属功能裁剪:若评审要求功能完整,需先行适配 interprocess 组件包。

## 查重差异

- consolation/libinput 条目覆盖 autotools/meson 侧与 musl 三件套;
  本条目以 interception 0.6.8 为载体补充 **cmake 裸名链接→pkg_check_modules**
  与 **Boost 缺组件时裁剪可选目标** 两个 cmake 侧模式,增量明确。

## 关联交付

- 本草稿与 `archives/i/interception/0.6.8/**` 及软件级 manifest 属同一
  交付范围(同 PR 关联,知识库扩展路径 B)。
