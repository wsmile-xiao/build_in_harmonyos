# DRAFT-geojson-cpp-0.5.1-mapbox-geometry-value-sharedptr-abi

> 旧版 mapbox feature::value 按值访问器与 mapbox-geometry 2.x shared_ptr 语义不兼容的适配迁移

## 问题特征（真实日志片段/标记）

- conan create G2 编译失败日志：
  - `geojson_value_impl.hpp:29: error: no matching member function for call to 'is'`
    （`val.is<value::array_type>()`，array_type 不再是 variant 成员类型）
  - `geojson_value_impl.hpp:60: error: variable 'valueObject' with type 'auto *' has incompatible initializer of type 'mapbox::feature::value::const_object_ptr_type' (aka 'shared_ptr<const unordered_map<...>>')`
  - `variant.hpp:332: error: no matching function for call to object of type 'mapbox::geojson::to_value'`
    （visit 对 shared_ptr 数组/对象类型无匹配访问器重载）
  - `test.cpp:177: error: no matching member function for call to 'is'`（`nested.is<mapbox::util::recursive_wrapper<values>>()`）

## 根因

- geojson-cpp 0.5.1（2020）面向旧版 mapbox-geometry：`feature::value` 的数组/对象
  直接按值存 `std::vector<value>` / `std::unordered_map<std::string, value>`，
  可直接用 variant 的 `is<T>()`/`get<T>()`。
- ohpcd 已发布的 mapbox-geometry/2.0.3（搭配 mapbox-variant/1.2.0）将
  `value_base` 的数组/对象改为 `std::shared_ptr<std::vector<value>>` /
  `std::shared_ptr<std::unordered_map<...>>`（`value::const_array_ptr_type` /
  `const_object_ptr_type`），提供 `getArray()/getObject()` 返回 shared_ptr。
- 旧代码三处依赖失效：① `is<value::array_type>()` 判型；② `auto *p = getObject()`
  裸指针声明；③ to_value/convert 访问器按 `const std::vector<value>&` /
  `const std::unordered_map&` 形参匹配 visit 派发。

## 修复方案（rec）（编号步骤，含具体文件与命令）

1. 生成最小适配补丁 `patches/0001-adapt-mapbox-geometry-2-value-abi.patch`：
   - `include/mapbox/geojson_value_impl.hpp`：
     - `val.is<value::array_type>()` → `val.getArray() != nullptr`
     - `auto *valueObject = val.getObject()` → `auto valueObject = val.getObject()`
       （shared_ptr，`->` 同用）
     - `is<value::object_type>()` → `is<value::object_ptr_type>()`
     - `const auto *featureArray = ...getArray()` → `const auto featureArray = ...`
     - convert(const value&) 的 object 分支 `[](const value::object_type&)` →
       `[](const value::object_ptr_type&)` 并 `convert<geojson>(value(*jsonObject))`
   - `include/mapbox/geojson_impl.hpp` to_value 访问器：
     `operator()(const std::vector<value>& array)` →
     `operator()(const value::const_array_ptr_type& array)`（循环 `*array`）；
     `operator()(const std::unordered_map<...>& map)` →
     `operator()(const value::const_object_ptr_type& map)`（循环 `*map`）；
     另补 `operator()(const value::object_type& map)` 重载供
     `element.properties`（plain map）直调。
   - `test/test.cpp`：nested 断言
     `is<recursive_wrapper<values>>/get<values>/get<prop_map>` →
     `getArray()/getObject()` 访问器（断言数值与语义不变）。
2. `conan-verify geojson-cpp 0.5.1`：G1-G4 全过，上游 30 用例 + 消费者 4 断言全过。

## 禁止策略

- 禁止保留旧按值访问器（`is<array_type>`/`get<values>`/`recursive_wrapper`）：2.x 无对应类型必失败。
- 禁止用 `--build=...` 或降级 mapbox-geometry 版本绕过（registry 无旧版）。
- 禁止删改上游测试断言语义，只允许类型访问方式迁移。

## 与相近条目的边界（查重）

- 官方只读快照 graph/doc 全量检索 `getArray/getObject/feature::value/value::const/recursive_wrapper` 零命中；
  drafts 中 DRAFT-mapbox-geometry-2.0.3-catch1-signed-urng-libcxx-compat-fix 为 Catch1.x URNG 兼容（不同故障面）。
- E499（运行时 libdir/LD_LIBRARY_PATH）、E216（glib/libxml2 components include 传播）均非等价。
- 本条目为 mapbox feature::value 由按值→shared_ptr 的 ABI 迁移模式，可跨库复用（任何旧 mapbox 生态消费者）。

## 适用判断

- 适用：消费 mapbox feature.hpp value 且按旧按值 API 编写的库，报 `no matching member function for call to 'is'/'get'`、
  `incompatible initializer ... const_object_ptr_type`、visit 无匹配访问器。
- 不适用：纯 geometry.hpp 类型（不碰 feature::value）的库、Catch2 等无关错误。
