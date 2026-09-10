# cmrc 2.0.1 适配笔记

## 编译环境
- 构建系统: cmake（纯 CMake 模块分发，无库无头）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64)
- 状态: built

## 编译步骤
- 官方源: https://github.com/vector-of-bool/cmrc/archive/refs/tags/2.0.1.tar.gz
- SHA-256: edad5faaa0bea1df124b5e8cb00bf0adbd2faeccecd3b5c146796cbcb8b5b71b
- conan create (ohos-aarch64 profile) 通过；conan-verify G1/G2/G3/G4 + L2/L4/L5 全 PASS
- 上游测试: ctest 7/7 通过（simple/flower/prefix/whence/whence_prefix/iterate/enoent）
- test_package: test_cmrc + test_ohos 消费者验证 CTest 2/2 通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conan-init 生成 autotools 模板 | init-build 按 URL 后缀误判构建系统 | 按源码实际（CMake 模块）重写 conanfile.py 为模块分发配方，manifest build_system 修正为 cmake |
| 2 | G1 报缺 build()/export_sources() | 模块分发配方未满足门禁 | 补 export_sources()(export_conandata_patches) 与 build()(apply_conandata_patches) |
| 3 | conan create: library 无 shared 选项 | Conan 2 强制 library 型声明 shared | 补 options={"shared":[True,False]} default False |
| 4 | package() 相对 dst 落入 build 目录 | copy() 相对路径解析到 build 目录 | dst 用 os.path.join(self.package_folder,...) 绝对路径 |
| 5 | test_package include 找不到 CMakeRC.cmake | 模块文件未装入包 lib/cmake/cmrc | package() 显式 copy 模块；cmake_build_modules 指向模块文件 |
| 6 | CMakeRC.cmake cmake_minimum_required(VERSION 3.3) 报错 | CMake 4.1.2 移除 <3.5 兼容 | patches/0001-cmake-minimum-3.5.patch bump 3.5（E103 覆盖） |
| 7 | cmrc_add_resource_library FILES 关键字报 No rule to make target '.../FILES' | cmrc API 不接受 FILES 关键字，资源路径作未解析参数 | test_package CMakeLists 去掉 FILES，直接传资源路径 |
| 8 | test.c 链接 undefined symbol: main | C++ 代码在 .c 文件中 | 重命名为 test.cpp |
| 9 | W3 JC5 命中其他库 .ci-trigger 基线 | util-linux-login 2.42.2 提交前已存在空基线文件 | 基线隔离复验（记录路径+pre SHA-256，git rm --cached 隔离，复跑 W3 通过，原样恢复核对 post SHA-256），见 reports/baseline-isolation-audit.md |

## 源码修改
- 无上游源码修改（不修改库本体），仅补丁 0001-cmake-minimum-3.5.patch 作用于 CMakeRC.cmake 最低版本

## 知识沉淀
- 纯 CMake 模块分发（无头无库无 install）的 Conan 配方四要素：
  lib/cmake 落位 + cmake_build_modules + builddirs + package_id clear
  → DRAFT-cmrc-2.0.1-cmake-module-distribution.md/.kv（路径 B，与归档同 PR）
- cmake_minimum_required <3.5 与 CMake 4.x 不兼容 → 复用 E103（bump-cmake-minimum-version）
