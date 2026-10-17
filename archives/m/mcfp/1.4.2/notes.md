# mcfp 1.4.2 — 适配记录

> 上游: https://github.com/mhekkel/libmcfp/archive/refs/tags/v1.4.2.tar.gz （GitHub 镜像，tag v1.4.2）
> sha256: dcdf3e81601081b2a9e2f2e1bb1ee2a8545190358d5d9bec9158ad70f5ca355e
> 工程类型: CMake (>=3.23), header-only C++20 INTERFACE library；BSD-2-Clause
> 用途: cif-tools 2.0.0 硬依赖（configure 时 CPM 从 forge.hekkelman.net 拉取，除非已预提供 mcfp target）

## 结论快照
- 产物: header-only（include/mcfp/*.hpp + mcfp/detail/*）+ CMake 配置（lib/cmake/mcfp，
  find_package(mcfp) → target `mcfp::mcfp`）。`package_type: header-library`，无二进制、无依赖。
- 上游自动化测试: test/unit-test.cpp（Catch2 v3.4.0，CPM 从 GitHub fetch，仅当 BUILD_TESTING
  AND PROJECT_IS_TOP_LEVEL）。conan build 置 BUILD_TESTING=OFF 避免 CI 禁网拉取 → 如实 NOT_RUN；
  功能验证放 test_package 消费者（真实跑 mcfp::config CLI 解析 API）。

## OHOS 关键适配（详见 conanfile.py）
1. `package_type: header-library`；`validate()` os 白名单 Linux/OHOS（R32）。
2. CMakeToolchain 在 OHOS 置 `CMAKE_SYSTEM_NAME=Linux`（视作 Linux-like 目标，同 fast_float）。
3. `BUILD_TESTING=OFF` + `BUILD_DOCUMENTATION=OFF`（上游 Catch2 走 CPM/GitHub，CI 禁网）。
4. 上游 CMake 安装原样执行（headers + mcfpConfig.cmake），conan CMakeDeps 对消费者自动生成
   find_package(mcfp)+mcfp::mcfp，满足 cif-tools 的 guard（mcfp_FOUND/libmcfp_FOUND/TARGET mcfp）。

## 依赖关系
- 编译/运行: 无（纯标准库 header-only）。test-only: Catch2（未启用）。
- 被依赖: cif-tools（先建本依赖库，再正式 requires mcfp/1.4.2）。

## 验证记录（true-device Harmony verify 后回填）
- [ ] HARMONY_VERIFY conan create PASS
- [ ] test_package 冒烟输出确认（consumer parse CLI: -n 7 --text hello → num=7/text=hello）
- [ ] CI 结果
