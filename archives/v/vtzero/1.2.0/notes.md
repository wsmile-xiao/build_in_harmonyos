# vtzero 1.2.0 适配笔记

## 编译环境
- 构建系统: cmake (header-only)
- 编译日期: 2026-08-28
- 编译器: clang/clang++
- 状态: built (本地验证通过，未发布)

## 编译步骤

vtzero 1.2.0 是 header-only C++14 库（Mapbox vector tile 编解码），
CMake 仅做配置与头文件安装：`install(DIRECTORY include/vtzero DESTINATION include)`。

本地验证（不依赖网络，直接编译消费者用例）：
```bash
clang++ -std=c++14 -I<vtzero/include> -I<protozero/include> \
  archives/v/vtzero/1.2.0/test_package/test_vtzero.cpp -o vtzero_test
./vtzero_test   # → PASS: vtzero encode/decode round-trip OK (layer='roads', features=1, tile_bytes=25)
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 CMake `find_package(Protozero 1.7.0 REQUIRED)` | vtzero 头文件包含 `<protozero/...>` | 配方 requirements() 声明 `protozero/1.8.2`（header-only 依赖，由 pc1-41 绑定） |
| 2 | 初始测试源码使用了不存在的 API (`layer.add_point_feature` / `vector_tile.layers`) | 对 vtzero 1.2.0 API 不熟悉 | 参照官方 examples/vtzero-create.cpp 改用 `point_feature_builder` + `add_point/commit` + `tile.next_layer()` |

## 源码修改

无补丁。上游源码零修改（header-only 直接可用）。

## 依赖版本

- protozero 1.8.2（header-only，pc1-41 适配中；本地验证使用
  /storage/Users/currentUser/tmp/builds/protozero-1.8.2.orig 头文件）
- OSRM v26.5.0 为已验证消费者（其 CMake 需要 vtzero/vector_tile.hpp）

## 验证结果

```bash
$ clang++ -std=c++14 -I include -I protozero/include test_vtzero.cpp -o vtzero_test
$ ./vtzero_test
PASS: vtzero encode/decode round-trip OK (layer='roads', features=1, tile_bytes=25)
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | header-only 配方 (package_type=header-library, cpp_info.libs=[]) |
| conandata.yml | 官方 URL + SHA-256: bdbd4a70404fbd6efc8588cc34065aa401b3bcd2533b532e68ff790267f4fc23 |
| test_package/ | 消费者往返测试 (encode→decode→verify layer name) |

## 注意事项

- 本轮任务 remote auth 关闭：未 commit/push/PR/上传制品；仅本地验证。
- vtzero 上游测试 test/ 依赖 catch + mvt-fixtures 子模块（tar 归档不含），
  CI 下厂商 CI 自行拉取；本地以 test_package 往返测试作为 L1 验证。

## r02 依赖消费与本地闭包 (2026-08-29, pc1-42)

### 依赖
- protozero/1.8.2 已由 PC1-42 任务消费验证：
  - `conan download protozero/1.8.2 -r=ohpcd --only-recipe` → 成功
    (recipe revision bf12a913593b6cb14831d4d44083e002, 2026-08-28 发布)
  - `conan create vtzero` 依赖解析从 ohpcd 拉取 protozero 二进制包
    6b129b068851896169fae42d399fa922d239ce8a (package revision 151c0f03dc05bd3688eacb2facb51eb1)
  - 源码下载: 官方 URL https://github.com/mapbox/vtzero/archive/refs/tags/v1.2.0.tar.gz
    SHA-256 = bdbd4a70404fbd6efc8588cc34065aa401b3bcd2533b532e68ff790267f4fc23 (与 conandata 一致)

### 配方修复（本任务实际修改，均在允许范围 archives/v/vtzero/1.2.0/）
1. `generators = "CMakeDeps", "CMakeToolchain"` → `"CMakeDeps",`
   (Conan 2: CMakeToolchain 同时声明于 generators 与 generate() 会报
   "should only be present in one of them")
2. generate() 注入 `PROTOZERO_INCLUDE_DIR` 缓存变量，指向 Conan 依赖
   protozero 的 include 目录。上游 CMakeLists 用
   `include_directories(SYSTEM ${PROTOZERO_INCLUDE_DIR})`，CMakeDeps
   CONFIG 模式只定义 protozero_INCLUDE_DIRS，导致上游 unit-tests/
   fixture-tests 缺 <protozero/...> 头文件路径而编译失败。

### 上游测试账本 (在 conan build 目录实际运行)
- ctest 全套: 12/12 Passed (vtzero-filter×5, vtzero-show×5,
  ext-tests-mapbox-streets-v6-14-8714-8017.mvt, unit-tests)
- unit-tests: 186 test cases / 1297 assertions, 全部通过 (exit 0)
  （必须在上游 test/ 工作目录运行；build_in_harmonyos 仓库根目录下
   相对路径 fixture 不可解析导致 23 用例失败——真实工作目录下全绿,
   已在 MANIFEST.yml 记录）
- fixture-tests: 需 FIXTURES_DIR 指向 mvt-fixtures 子模块 (未随 release
  归档)，未直接运行；ext-tests 已通过 ctest 覆盖。
- test_package 消费者往返: PASS (layer='roads', features=1, tile_bytes=25)

### 门禁
- conan-verify: G0/G1/G2/G3/G4 全部 PASS (exit 0)，可标记 published
- conan create: exit 0；W3 本地闭包完成
---

**编译结束**: 2026-08-29 19:32
**最终状态**: built
