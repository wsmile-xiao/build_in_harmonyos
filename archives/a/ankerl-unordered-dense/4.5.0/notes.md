# ankerl-unordered-dense 4.5.0 适配笔记

## 编译环境
- 构建系统: cmake（上游 INTERFACE target）/ meson（上游测试）
- 编译日期: 2026-08-29
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-unknown-linux-ohos)
- 状态: built

## Bootstrap 来源核验（2026-08-29）

- 官方仓库: https://github.com/martinus/unordered_dense （default_branch=main, archived=false, 1460 stars）
- 正式标签: v4.5.0（lightweight tag，解引用 commit 73f3cbb237e84d483afafc743f1f14ec53e12314）
- GitHub release: v4.5.0, published_at=2024-12-03T18:38:21Z, target_commitish=main
- 官方 tarball: https://github.com/martinus/unordered_dense/archive/refs/tags/v4.5.0.tar.gz
- tarball sha256（实测下载值）: 2364ce4bc4c23bd02549bbb3a7572d881684cd46057f3737fd53be53669743aa
- 逐文件核对（GitHub git trees API, commit 73f3cbb2...）:
  - CMakeLists.txt blob b5f4c4fa739ead7bcfd5ce9ff0d2741918fcf2d3 == tarball 内 git hash-object ✅
  - LICENSE blob c4d1a0e48eba077622a1aeb77522ab008b196bfc ✅
  - meson.build blob a6bdc47c9e636b9a1d196321611a8081e07bd113 ✅
  - include/ankerl/unordered_dense.h blob 13484a9817b9ce598622b791c603588491be8957 ✅
- 结论: tarball 与官方 tag commit 一致，来源可信。

## 首轮 Adapt

- header-only C++17 库：唯一公开头文件 `include/ankerl/unordered_dense.h`
- 配方 package() 只拷贝该头文件（对齐上游 CMake `install(DIRECTORY include/ankerl)`）
- cmake_file_name=unordered_dense / cmake_target_name=unordered_dense::unordered_dense（与上游 CMake 包名一致；注意与 conan 包名 ankerl-unordered-dense 不同）
- 无外部依赖（W0 预检：无依赖，conan create 无 --build=missing 拉取）
- 无补丁，源码未修改
- test_package: 消费者视角编译+运行 map/set 实质用例（R34，含 robin-hood backward shift 删除、emplace、迭代验证）

## 验证结果

见 reports/（conan-verify W3 本地验证日志）。

## 注意事项

- header-only 无 .a/.so 产物；G3/R26 无系统同名库冲突
- 上游测试为 meson 驱动（test/meson.build），header-only 包以 test_package 消费者验证替代
---

**编译结束**: 2026-08-29 22:43
**最终状态**: built
