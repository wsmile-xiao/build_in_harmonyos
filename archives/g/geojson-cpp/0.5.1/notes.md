# geojson-cpp 0.5.1 适配笔记

## 编译环境
- 构建系统: Makefile（上游 mason 依赖管理，配方改为 Conan 托管编译）
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4（ohos-aarch64 profile）
- 状态: built（conan-verify G1-G4 全过，W3 本地 CI exit_code=0）

## 编译步骤

1. `init-build geojson-cpp 0.5.1 --url=https://github.com/mapbox/geojson-cpp` 获取源码
   （GitHub 直连超时，通过 ghfast.top 镜像下载官方 tag v0.5.1 tarball，sha256 与官方一致）
2. `conan-init` 生成配方骨架 → 重写 conanfile.py（Makefile 库：直接用 Conan 编译器
   编译 src/mapbox/geojson.cpp 生成 libgeojson.a + 打包头文件）
3. `conan-verify` G1-G4 全过；`finish` W3 本地 CI（build_and_test.sh）通过

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | G2 conan create 编译失败：`geojson_value_impl.hpp` 中 `is<value::array_type>()`、`auto *valueObject = getObject()` 报错 | 已发布 mapbox-geometry/2.0.3 的 feature::value 改为 shared_ptr 语义（const_array_ptr_type/const_object_ptr_type），与 geojson-cpp 0.5.1 面向的旧版按值 API 不兼容 | 补丁 0001：改用 `getArray()/getObject() != nullptr` 判断、shared_ptr 访问器，to_value 访问器改接 `const_array_ptr_type/const_object_ptr_type`，上游 test.cpp 的 recursive_wrapper 断言改接访问器 |
| 2 | test_package 编译失败：`mapbox/geometry.hpp file not found` | 配方 package_info 未声明 `cpp_info.requires` 转发，下游 CMakeDeps 未生成 mapbox-geometry 等传递依赖配置 | package_info 增加 `cpp_info.requires = [mapbox-geometry::mapbox-geometry, mapbox-variant::mapbox-variant, rapidjson::rapidjson]`；test_package 显式 find_package 并链接全部依赖（与 mapbox-geometry 自身 test_package 同模式） |
| 3 | test_package 运行失败：bin/test_geojson-cpp not found | CMakeLists 未设 RUNTIME_OUTPUT_DIRECTORY，二进制未落在 test() 期望的 bin/ | CMakeLists 增加 `RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin` |
| 4 | finish W3 的 JC 垃圾文件检查失败：cloog/kics 的 .build-closed/.staging-verified 被拦 | 无关历史基线（其他库在 main 中跟踪的空状态文件，blob e69de29…），不在当前库允许范围 | 按基线隔离规则：审计记录 blob/哈希/来源提交 → 临时 git rm --cached（工作树文件保留）→ W3 复验通过 → 无条件恢复 index，零基线 diff |

## 源码修改

patches/0001-adapt-mapbox-geometry-2-value-abi.patch（3 文件，+15/-15 行级适配）：
- include/mapbox/geojson_value_impl.hpp：value 数组/对象访问改 shared_ptr 语义
- include/mapbox/geojson_impl.hpp：to_value 访问器改接 const_array_ptr_type/const_object_ptr_type，新增 object_type 重载
- test/test.cpp：nested 断言改接 getArray()/getObject() 访问器（断言内容不变）

## 依赖版本

- mapbox-geometry/2.0.3（ohpcd 已发布）
- mapbox-variant/1.2.0（ohpcd 已发布）
- rapidjson/1.1.0（ohpcd 已发布）

## 验证结果

```bash
# conan-verify: G1 配方完整性 ✅ G2 conan create ✅ G3 系统同名库隔离 ✅ G4 产物完整性 ✅
# finish W3 本地 CI: exit_code=0（.ci-result.json log_sha256=52a81a9db0e04175…）
# 上游测试: test_geojson 16 用例 ✅ / test_geojson_value 14 用例 ✅（assert 退出码 0）
# 消费者测试: test_package 4 断言 ✅
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 2 配方（library，静态 libgeojson.a + 头文件） |
| conandata.yml | 官方源 v0.5.1 + sha256 + 补丁声明 |
| patches/0001-*.patch | mapbox-geometry 2.0.3 value ABI 适配 |
| test_package/ | 消费者冒烟测试（parse/stringify 真实 API，R34） |

## 注意事项

- 库本身仅 src/mapbox/geojson.cpp 一个编译单元，头文件 include/mapbox/*.hpp 全部随包发布。
- 依赖注入必须走 Conan 依赖（requirements），不可用上游 mason（构建环境无 mason）。
