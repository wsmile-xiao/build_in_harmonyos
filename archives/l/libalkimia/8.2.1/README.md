# libalkimia 8.2.1 — 鸿蒙 PC conan 制品

`os=OHOS, arch=armv8`(= aarch64) 的 conan 包。上游 KDE 模块名为 `alkimia`，
安装的 CMake 包名为 `LibAlkimia6`；本归档按**平台任务/Conan 包名 `libalkimia`**
命名（`conanfile.py` 的 `name`、归档目录、test_package 声明、文档、测试输出串五点一致）。

## 能力与产物

- `AlkValue`：基于 GMP `mpq_class` 的多精度金额（解析/四则运算/舍入/精度换算）
- `AlkOnlineQuote` / `AlkOnlineQuoteSource` / `AlkOnlineQuotesProfile`：在线报价获取、
  解析与报价源持久化存储
- `AlkNewStuffEngine` / `AlkNewStuffStore`：在线报价源仓库（KNS）
- 产物：`lib/libalkimia6.so(.8/.8.2.1)`、`lib/libqmlalkimia6.so`、
  `include/alkimia/Qt6/alkimia/`（16 头文件）、
  `lib/cmake/LibAlkimia6-8.2/LibAlkimia6Config.cmake`（`Alkimia::` 命名空间）、
  `bin/onlinequoteseditor6` 工具、`share/` 资源

## 出包（鸿蒙 PC CI）

```bash
# 鸿蒙 PC 设备原生编译
conan create . -pr ohos-native
```

源码由 `conandata.yml` 的 url 在 `conan create` 时下载并 sha256 校验（`source()` 用 `get()`）。

## 消费

```bash
conan install --requires=libalkimia/8.2.1 -pr ohos-native
```

```cmake
find_package(LibAlkimia6 8.2.1 REQUIRED)
target_link_libraries(my_app PRIVATE Alkimia::alkimia Qt6::Core Qt6::Network)
```

`AlkOnlineQuoteSource`/`AlkOnlineQuotesProfile` 的头文件包含 `<KSharedConfig>`，
消费者需同时链接 `KF6::ConfigCore`（`LibAlkimia6Config.cmake` 通过
`find_dependency(KF6Config)` 提供该目标）。

## 测试

- 上游：`ctest --output-on-failure`（离线口径 9/9 通过；3 个网络型目标经
  `ctest -E` 排除，原因见 `notes.md` / `reports/upstream-test-evidence.md`）
- 消费者端到端：`test_package/test_libalkimia.cpp`，23 个校验点，本地与
  DAYU200 真机均 23/23 通过（`reports/device-e2e-evidence.md`）
