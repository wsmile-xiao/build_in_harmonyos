# yyjson 0.13.0 — Conan 配方与验证记录

## 上游与来源

- 上游仓库：<https://github.com/ibireme/yyjson>
- 上游标签：`0.13.0`
- 下载地址：`https://codeload.github.com/ibireme/yyjson/tar.gz/refs/tags/0.13.0`
- SHA-256：`34e0f62a2bc11ab20d601e8ca1cc2b2079503aa45119a19133d89d19b94a0fae`
- CMake 以 `YYJSON_BUILD_TESTS=ON` 构建，并在打包前执行上游 CTest。

## 验证结果

真机使用独立 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-yyjson`，命令：

```sh
conan create archives/y/yyjson/0.13.0 \
  -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --no-remote
```

- `conan create`：退出码 0。
- 上游 CTest：12/12 通过；配方 `cmake.test()` 执行 CMake 的 `test` 目标，输出显示 12 个 CTest 全部通过。
- 消费者测试：1/1 通过；通过 Conan `test_package` 构建并运行 `test_yyjson`。
- 产物：`libyyjson.a`、`yyjson.h`、CMake 配置与 pkg-config 文件。

本配方不声明 Conan 依赖；`--no-remote` 用于避免不可达的 ConanCenter 查询。