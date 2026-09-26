# confu_json

confu_json 是一个 C++20 JSON 序列化/反序列化库：对任意通过
`BOOST_FUSION_ADAPT_STRUCT` 适配的结构体，提供 `confu_json::to_json` /
`confu_json::to_object` 完成与 JSON 的双向转换（支持 enum、optional、
unique_ptr、vector、嵌套结构体及 Base→Derived 映射动态派发）。

## 特性
- **Header-only**：纯头文件库（`include/confu_json/`），无需编译二进制
- **CMake INTERFACE library**：通过 CMake 安装公开头文件
- **依赖**：magic_enum（枚举序列化）、boost（fusion/mpl/optional/json）
- **C++20**：需 C++20 编译器

## OHOS 适配（1.2.4）
- 官方源：https://github.com/werto87/confu_json （tag v1.2.4，
  SHA-256 `adb87ecd8181f4ac4bb1eac0fbd9d803ce2f4c5bb7982b84b8a1aa95814228c5`）
- 6 个适配补丁：compile_commands 守卫、boost 头文件-only 链接（SYSTEM include）、
  boost::mpl 依赖类型补 `typename`、上游测试移除未发布的 durak 依赖
- 上游测试：49 个 TEST_CASE，47/49 实例化并全部通过（123 断言）；
  2 个依赖 durak 的用例未实例化（durak 未发布到 ohpcd，含恢复条件）
- 消费者用例与 OHOS 专项测试均通过（见 `1.2.4/reports/` 与 `1.2.4/ohos_test/`）
