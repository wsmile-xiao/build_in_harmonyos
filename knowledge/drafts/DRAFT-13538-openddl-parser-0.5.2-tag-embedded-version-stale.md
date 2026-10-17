# DRAFT-13538-openddl-parser-0.5.2-tag-embedded-version-stale

## 问题

openddl-parser 官方 tag `v0.5.2` 下的源码，`code/OpenDDLParser.cpp` 仍写死：

```cpp
static const char *Version = "0.4.0";
```

CMakeLists.txt 用正则从该 cpp 读取 PROJECT_VERSION（`string(REGEX MATCH ...)`），
因此 configure/编译产物中 `OpenDDLParser::getVersion()` 返回 "0.4.0"，而不是
tag 版本 0.5.2。上游在 v0.5.2 tag 上没有同步内嵌版本号字符串。

```
$ ./bin/openddlparser_unittest 2>/dev/null | tail -1
[  PASSED  ] 125 tests.
$ ./bin/openddl_parser_demo --help 2>&1 | head -1
OpenDDL Parser Demo version 0.4.0
```

## 根因

- 上游将版本号维护在 cpp 源码常量里（`static const char *Version`），发布新 tag 时
  忘记同步更新该常量（v0.5.2 仍为 0.4.0）。
- 提供 `getVersion()` 运行时 API 的库类软件，其配方/归档版本与源码内嵌版本可能
  不一致；CMake 从源码提取版本号时会把错误版本带入构建信息与安装产物。

## 处理口径（可跨库复用）

1. **配方/归档版本以官方 tag 为准**（conandata.yml 的 url/sha256 绑定 v0.5.2
   tarball，conanfile.py `version = "0.5.2"`），**不**跟随源码内嵌版本字符串。
2. **不修改上游源码**（不 patch 版本字符串）——修改会引入与官方 tag 的 diff，
   且不影响编译/测试结果；返回旧版本串属上游事实，在 notes.md / PR 正文如实声明。
3. **CMake 版工程注意**：`PROJECT_VERSION` 读自源码时与 tag 不一致只是信息性
   差异；若上游用 `PROJECT_VERSION` 生成安装文件名/头文件宏，需在配方
   `generate()` 显式覆盖正确的 tag 版本（本库未用该值生成文件名，无需覆盖）。
4. **测试/消费者断言不得硬编码版本字符串**：断言"能调用 getVersion() 且非空"，
   不断言等于 tag 版本，避免把上游事实误判为适配失败。

## 验证

- 本库 conan-verify（ohos-aarch64）通过：上游 gtest 125/125 PASSED，
  test_package 消费者（parse/getRoot/getChildNodeList/getType/getProperties 公开
  API）通过，consumer 用例与 test_ohos 专项（ELF64 AArch64 / musl / 无宿主路径
  泄漏 / 真实解析）全部通过。
- `getVersion()` 返回 "0.4.0" 已在 notes.md 与 PR 正文如实声明。

## 适用边界

- 适用：从源码内嵌常量读取版本号并提供运行时版本 API 的 C/C++ 库（OpenDDL 解析、
  序列化、编解码类），tag 发布未同步常量时。
- 反例：版本号由 configure/CMake option 显式传入的工程（无此问题）；上游用
  git describe 动态生成版本的工程（版本会随 tag 正确）。

## 关系

- similar_to: DRAFT-8425-libusbsio（版本语义拆解：包版本 vs 内嵌产物版本两条线；
  彼为上游源删除场景，此为源存在但内嵌串未同步场景，处理方向互补）
- conflicts_with: 无