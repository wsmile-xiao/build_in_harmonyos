# ki18n 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-19
- 编译器: clang/clang++
- 状态: built

## 编译步骤

conan create archives/k/ki18n/6.26.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(Gettext REQUIRED) 失败 | OHOS 无 msgmerge | patch REQUIRED->QUIET |
| 2 | Could NOT find LibIntl | conan_cmakedeps_paths.cmake 不含 gettext 路径 | 在 generate() 中向 conan_cmakedeps_paths.cmake 添加 gettext include/lib 路径 |

## 依赖版本

- qtbase/6.11.1
- gettext/0.22.5
- ecm/6.26.0 (build tool_require)

## 验证结果

conan create PASS (Round 2), test_package 1/1 passed

## 构建产物

- libKF6I18n.so, libKF6I18nLocaleData.so, KF6I18nConfig.cmake

## 关键修复

conan_cmakedeps_paths.cmake 必须显式 PREPEND gettext include/lib 路径，否则 FindLibIntl 找不到 libintl.h/libintl.a。根因：CMakeToolchain 的 set(CMAKE_INCLUDE_PATH ... CACHE) 不覆盖 normal scope 中已有的 list 值；当 conan_cmakedeps_paths.cmake 存在时，conan_toolchain.cmake 的 else()-block (含 gettext 路径的 list PREPEND) 被跳过。

## 跨轮遗留记录（C 类）

- **软件级文件缺失**：archives/k/ki18n/ 下无软件级 manifest.yaml 与 README.md
  （ARCHIVE-SPEC v3.0 §2.1 列为"必须"）。基线 6.14.0（build_in_harmonyos 与
  worktree 内均）同样缺失，属跨轮重复问题（C 类，review finding P2-003），
  本次不新增。ki18n 为库类型（无 bin/ 产物），commands.json 不需要（R38）。
