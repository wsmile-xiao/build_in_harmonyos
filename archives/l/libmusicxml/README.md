# libmusicxml

libmusicxml 是 Grame 维护的便携 C++ 库，贴近 MusicXML 乐谱交换格式，
提供解析、访问与 Guido 转换等高级 API。

## HarmonyOS PC adaptation

- 基于官方 v3.22 源码构建，C++17，CMake 工程入口位于 `build/CMakeLists.txt`。
- 关闭示例工具（`GENTOOLS=OFF`），产物为纯库（共享 `musicxml` / 静态 `musicxml2`），无外部依赖。
- 上游无自动化测试套件（`build/CMakeLists.txt` 无 `enable_testing`/`add_test`，全仓无 gtest 痕迹，`validation/` 仅为手工工具 Makefile），已在版本 `test_package/MANIFEST.yml` 中审计声明。
- OHOS 下补齐共享库 SONAME/RPATH 契约，运行前对测试 ELF 签名。

## Consumer verification

`test_package` 调用 `musicxmllibVersion`/`musicxmllibVersionStr` 并用
`musicxmlstring2guido` 转换最小乐谱，校验返回码与 Guido 输出非空（4 检查）。

## Reference

- https://github.com/grame-cncm/libmusicxml
