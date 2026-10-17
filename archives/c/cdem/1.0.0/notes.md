# cdem 1.0.0 — OHOS 适配笔记

## 来源核验
- 官方仓库：https://github.com/connected-digital-energy-meter/connected-digital-energy-meter
- 正式标签：`v1.0` → version 1.0.0（library.properties 声明 1.0.0）
- 源码 tarball：`https://codeload.github.com/connected-digital-energy-meter/connected-digital-energy-meter/tar.gz/refs/tags/v1.0`
- SHA-256：`d54d1fefe9042f4ebbeb44c6cd540d99ffebe8181e1917eac4dc8ec3d8e81d0b`（实测 25662 字节）
- 许可证：MIT
- 发布日期：2021-06-04（GitHub Release v1.0）

## 结构
- 上游为 Arduino 库（`src/` + `library.properties`），依赖 ArduinoJson、PubSubClient，目标架构 `esp8266`
- 核心头文件 `src/CDEM.h` 包含大量 Arduino 专有头文件，无法直接在 HarmonyOS 上编译
- 本适配在 `source()` 阶段生成 portable 头文件 `include/cdem/cdem.h` 与配套 `cdem.c`，提供与上游概念一致但不依赖 Arduino 的 API：
  - `cdem_create` / `cdem_destroy`
  - `cdem_version_major/minor/patch/string`
  - `cdem_parse_telegram` / `cdem_get_line_count`
- CMake 采用 INTERFACE library，`install(DIRECTORY include/...)` 安装头文件

## 依赖
- 无第三方依赖，仅 C 标准库

## OHOS 适配要点
- 剥离 Arduino 依赖：不编译上游的 `src/`，仅安装生成的 portable header
- header-only：`package_type = "header-library"`，`build()` 仅执行 `cmake.configure()` + `cmake.build()` 以验证 CMake 语法
- 保留上游 MIT 许可证与版本字符串

## 上游测试审计
- 上游 tarball 内无 `test/`、`tests/`、`CMakeLists.txt` 的 test target，也无 `library.json` 以外的测试定义
- 已审计 `src/`、`tools/`、`library.json`、`library.properties`：确认无任何可执行的上游测试套件
- 因此 `test_package/MANIFEST.yml` 标记 `upstream_tests_exist: false` 并提供审计说明；`build()` 阶段不执行上游测试

## 本地验证
- 待 HMBS 真机预检：`conan create` 应通过，`test_package` 的 6 断言应全部通过
