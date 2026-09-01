# unordered_dense 4.9.2 适配笔记

## 编译环境
- 构建系统: cmake（上游 INTERFACE target）/ meson（上游测试）
- 编译日期: 2026-09-01
- 编译器: clang/clang++ (OHOS SDK, aarch64-linux-ohos)
- 状态: built

## Bootstrap 来源核验（2026-09-01）

- 官方仓库: https://github.com/martinus/unordered_dense
- 正式标签: v4.9.2（官方 tag）
- 官方 tarball: https://github.com/martinus/unordered_dense/archive/refs/tags/v4.9.2.tar.gz
- tarball sha256（实测下载值）: abe3b267cbec3094bd7ca84a9990d7723a8d3dda141e08c67e295e3175f6ee28
- 内容核验:
  - CMakeLists.txt `project("unordered_dense" VERSION 4.9.2 ...)` ✅
  - include/ankerl/unordered_dense.h 版本宏 MAJOR=4 / MINOR=9 / PATCH=2 ✅
  - 归档根目录名 unordered_dense-4.9.2，1305 个文件 ✅
- 结论: tarball 与官方 v4.9.2 tag 一致，来源可信（本机 github 直连超时，经 gh-proxy 官方归档镜像下载后核验）。

## 首轮 Adapt

- header-only C++17 库：公开头文件 `include/ankerl/unordered_dense.h` 与 `include/ankerl/stl.h`
- 配方 package() 拷贝整个 `include/ankerl` 目录（对齐上游 CMake `install(DIRECTORY include/ankerl)`）
- cmake_file_name=unordered_dense / cmake_target_name=unordered_dense::unordered_dense（与上游 CMake 包名一致；conan 包名即 unordered_dense）
- 无外部依赖（W0 预检：无依赖，conan create 无 --build=missing 拉取）
- 无补丁，源码未修改
- test_package: 消费者视角编译+运行 map/set 实质用例（R34，含 robin-hood backward shift 删除、emplace、迭代、set 去重验证）

## 验证结果

见 reports/（conan-verify W3 本地验证日志）。

## 注意事项

- header-only 无 .a/.so 产物；G3/R26 无系统同名库冲突
- 上游测试为 meson 驱动（test/meson.build，77 个 unit），header-only 包以 test_package 消费者验证替代；上游测试统计见 reports/upstream-tests.md
- 与 archives/a/ankerl-unordered-dense/4.5.0（不同库名/版本的旧归档）区分：本归档为 unordered_dense 4.9.2，不混用
---

**编译结束**: 2026-09-01 04:09
**最终状态**: built
