# sfarklib 2.24 HarmonyOS PC 适配说明

## 基本信息

- 上游仓库：https://github.com/raboof/sfArkLib
- 源码版本：标签 `2.24`，提交 `e558feb824132d71004af82cc3a235566b89bec8`
- 源码 SHA-256：`f1539666c03779a74018f6e6f0da60bcf2be687d87d9cb71e23dcc8c5213fa2f`
- 目标平台：HarmonyOS PC aarch64
- 构建工具：Conan 2.29.1、Clang 15、llvm-ar
- 依赖：`zlib/1.3.1`
- 状态：built

## 构建方式

配方从官方标签归档下载源码，将三个待打补丁文本文件的 CRLF
行尾规范化为 LF，随后通过 `apply_conandata_patches()` 应用补丁。七个
C++ 源文件使用 OHOS Clang、`-D__LITTLE_ENDIAN__` 和 `-fPIC` 编译，
最终由 llvm-ar 生成 `libsfark.a`。zlib 作为公开 Conan 依赖传递给消费方。

## 适配问题与解决方案

| 问题 | 根因 | 解决方案 |
| --- | --- | --- |
| 真实 sfArk 文件在 64 位平台将许可证长度解析成巨大数值 | 上游以 `long` 表示格式规定的 32 位字段，而 OHOS aarch64 使用 LP64 | 将格式字类型改为 `uint32_t`/`int32_t` |
| `uncompress()` 长度参数类型不匹配 | zlib 要求 `uLongf *`，上游传入自定义整数指针 | 局部长度变量改为 `uLongf`，返回时显式转换 |
| 32 位无符号值的诊断格式不正确 | 修复字段宽度后仍使用 `%ld` | 使用与 `uint32_t` 一致的 `%u` |

## 补丁

- `patches/0001-sfklCoding.cpp.patch`：修正 32 位无符号值的格式化输出。
- `patches/0002-sfklZip.cpp.patch`：使用 zlib 定义的输出长度类型。
- `patches/0003-wcc.h.patch`：固定 sfArk 格式字段及长音频字的位宽。

补丁均为通用 LP64 可移植性修复，未引入 HarmonyOS 条件宏。

## 测试

上游 2.24 源码不含测试目录、测试源文件、测试框架或 `test`/`check`
目标，上游实测用例数为 0。适配新增 1 个 HarmonyOS 专用消费者测试，
包含 7 个断言，覆盖公开版本接口、解码错误路径、四类应用回调和输出文件安全。

验证结果：

- 项目 `conan-verify`：通过。
- HarmonyOS PC 真机 `conan create`：构建通过；新增测试 1/1、断言 7/7 通过。
- 真机真实样本解码：成功；生成文件 SHA-256 为
  `82475b91a76de15cb28a104707d3247ba932e228bada3f47bba63c6b31aaf7a1`，
  与上游原始 SoundFont 完全一致。

## 交付内容

- 头文件：`include/sfArkLib.h`
- 静态库：`lib/libsfark.a`
- 许可证：`licenses/COPYING`
