# kcompletion 6.26.0.1 适配修复笔记

## 背景
- 上游版本: 6.26.0（制品仓已发布 6.26.0）
- 本版本: 6.26.0.1（E537 relocatable 修复，因制品仓不支持同版本多 recipe revision）
- 分支: fix/kcompletion-6.26.0.1
- 编译日期: 2026-09-30
- 构建系统: cmake（KDE ECM 工程）

## 修复根因
kcompletion 6.26.0 制品中 `libKF6Completion.so` 的 DT_NEEDED 记录了**构建机 Conan cache 绝对路径**
（`/storage/Users/currentUser/.cache/conan2/p/kconf7db3dce604ff1/p/lib/libKF6ConfigGui.so` 等），
因为依赖 kconfig/kwidgetsaddons 发布时**无 DT_SONAME**，CMake 按 IMPORTED_LOCATION 绝对路径链接，
ld 将机器私有路径写入 DT_NEEDED（E537）。下游消费方（如 ktextwidgets）运行期加载
`libKF6Completion.so` 时依赖解析失败（5/5 上游 CTest 全红）。

## 修复方案（E537，ksanecore/kpackage 26.04.0/6.26.0 先例）
1. **0001-CMakeLists.txt.patch**：顶层对 `KF6::ConfigCore`/`KF6::ConfigGui`/`KF6::WidgetsAddons`
   stamp `IMPORTED_SONAME`（取 TARGET_FILE_NAME）+ 清除 `IMPORTED_NO_SONAME`(_RELEASE)，
   使 CMake 按 `-L<dir> -l:libKF6*.so` 链接。
2. **0002-src-CMakeLists.txt.patch**：`src/CMakeLists.txt` 用
   `target_link_directories(KF6Completion PRIVATE ${KCOMPLETION_DEP_LIB_DIRS})` +
   裸 `-lKF6ConfigCore`/`-lKF6ConfigGui`/`-lKF6WidgetsAddons` 链接（替代 KF6::* target），
   include 目录经 `INTERFACE_INCLUDE_DIRECTORIES` 提取为 SYSTEM PRIVATE 保留，
   产物 DT_NEEDED 记录 basename（可迁移）。
3. **conanfile.py**：版本 6.26.0.1；generate() 注入 `KCOMPLETION_DEP_LIB_DIRS`
   （kconfig/kwidgetsaddons 的 lib 目录，供裸 -l 链接的 -L 使用）。

## 依赖
- qtbase/6.11.1、kcodecs/6.26.0、kconfig/6.26.0、kwidgetsaddons/6.26.0
- tool_requires: ecm/6.26.0

## 验证
- conan-verify G0-G4 全通过（修复后上游测试可加载依赖）
- 上游 autotests: kcompletioncoretest / klineedit_unittest / kcombobox_unittest / ksortablelisttest / kemailvalidatortest

## 交付物
- conanfile.py（6.26.0.1）、conandata.yml、manifest.yaml、notes.md、test_package/、patches/0001+0002

## 对话记录
- 任务：ruqola 2.8.1 依赖项链修复；kcompletion 是 ktextwidgets 的直接依赖（ktextwidgets 上游测试加载 libKF6Completion 失败暴露此缺陷）
- 用户授权启动 kcompletion 修复后独立 PR【依赖项】

**编译结束**: 2026-09-30
**最终状态**: built（待 CI 发布后置 published）
---

**编译结束**: 2026-09-30 11:36
**最终状态**: built
