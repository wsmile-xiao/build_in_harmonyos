# ls-hpack 2.3.5 (HarmonyOS PC)

[ls-hpack](https://github.com/litespeedtech/ls-hpack) 是 LiteSpeed 开发的
HPACK（RFC 7541，HTTP/2 头部压缩）编解码库，是 lsquic 的核心依赖之一。

## 包信息

| 项目 | 值 |
|---|---|
| 上游 | https://github.com/litespeedtech/ls-hpack |
| 版本 | 2.3.5（tag `v2.3.5`） |
| License | MIT |
| SHA256 | `430a1a36029e0ae1c81eaa0b2356920f1e65fde1cdd722351c671ebe513b7a96` |
| 构建系统 | CMake（上游 `CMakeLists.txt`） |
| 包类型 | static-library（`libls-hpack.a`） |
| 依赖 | 无（xxhash 通过上游 `LSHPACK_XXH` 内置于 `deps/xxhash`，符号未导出外部依赖） |

## 说明

- 上游 `CMakeLists.txt` 没有 `install()` 规则，recipe 的 `package()`
  手动收集 `lshpack.h`、`lsxpack_header.h` 与构建产物 `libls-hpack.a`。
- 上游 `CMAKE_MINIMUM_REQUIRED(VERSION 2.8)` 过老，新 CMake（≥3.27）
  需要 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`（recipe 已内置）。
- 上游 `bin/` CLI 工具仅在 `CMAKE_SYSTEM_NAME == Linux` 时构建；
  OHOS 目标下为纯库包，无 commands.json。
- OHOS clang15/musl 下零 patch，直接编译通过。

## 上游测试

上游官方测试位于 `test/`（`test_hpack.c` + `test_int.c`，经 CTest
驱动）。上游 CMake 在非 Release 构建类型下自动启用
`ENABLE_TESTING()` 并附加 `-fsanitize=address`。

recipe 在 `build()` 阶段（非 Release）通过 `ctest` 在鸿蒙 PC
（aarch64/musl）上实际运行上游测试。

## test_package

验证最终包的公共 API（`lshpack.h`）：

- RFC 7541 Appendix C 官方向量解码（C.2.4 字面量、C.6.1 完整
  响应头集合），name/value 逐字节精确比较
- 静态表行为：`0x82`（`:method: GET`）解码精确匹配
- 多 header 编码 + round-trip（含 UTF-8 非 ASCII 值），两轮
  （第二轮验证动态表/索引状态）
- 错误/截断输入：解码器必须返回负值而非崩溃

## 使用示例

```cmake
find_package(ls-hpack REQUIRED)
target_link_libraries(mytarget PRIVATE ls-hpack::ls-hpack)
```
