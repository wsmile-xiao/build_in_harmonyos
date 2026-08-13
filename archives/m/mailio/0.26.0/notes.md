# mailio 0.26.0 适配笔记

## 当前状态

配方在 OpenHarmony PC 目标平台（aarch64）上完成了全新的 Conan 构建
（`conan create`）。共享库 `libmailio.so` 构建成功，消费者测试包在
目标上签名后执行通过。

- **构建方式**：共享库（BUILD_SHARED_LIBS=ON）
- **测试包**：编译、链接、签名、在 OHOS 目标上执行 — 通过
- **CI 干净构建**：boost/1.90.0.4 + mailio/0.26.0 从源码重建 — 通过
- **L4 安全扫描**：BIND_NOW + GNU_RELRO + NX 栈 — 通过

## 源码与提取边界

配方使用 GitHub 官方发布归档（tag 0.26.0），SHA256 为
`f3222adf2d5d8d8f89c5509a6da10dd6456637f32b3962c3c0c9af54178849dc`。
源码以 `.tar.gz` 格式下载，使用 `strip_root=True` 解压。

未应用任何补丁 — 上游 CMakeLists.txt 在 Conan 工具链提供正确的
编译器和标志后，可在 OHOS 上直接构建。

## 依赖说明

mailio 0.26.0 需要两个编译型依赖：

1. **Boost**（`boost/1.90.0.4`）— 组件 `date_time` 和 `regex`
   - `date_time` 是编译型库（`libboost_date_time.so`）
   - `regex` 在 Boost 1.90.0 中是纯头文件库（INTERFACE 库，无 `.so`），
     但头文件已正确安装
   - boost 配方从 1.90.0.3 扩展而来，在 `BOOST_INCLUDE_LIBRARIES` 和
     `package_info()` 组件列表中新增了 `date_time` 和 `regex`

2. **OpenSSL**（`openssl/3.5.6`）— 组件 `SSL`
   - 上游 CMakeLists.txt 调用 `find_package("OpenSSL" COMPONENTS "SSL")`
     并链接 `OpenSSL::SSL`
   - 本地 OpenSSL conan 配方未定义命名组件，因此使用 CMakeDeps 属性映射：
     `deps.set_property("openssl", "cmake_file_name", "OpenSSL")` 和
     `deps.set_property("openssl", "cmake_target_name", "OpenSSL::SSL")`

## 构建与打包契约

- **构建系统**：CMake（上游 `CMakeLists.txt`，最低 3.30.0）
- **C++ 标准**：C++17（`CMAKE_CXX_STANDARD 17`，`CMAKE_CXX_STANDARD_REQUIRED ON`）
- **构建选项**：
  - `BUILD_SHARED_LIBS` = `self.options.shared`（默认：True）
  - `MAILIO_BUILD_TESTS` = False（禁用；上游测试需要网络连接）
  - `MAILIO_BUILD_EXAMPLES` = False
  - `MAILIO_BUILD_DOCUMENTATION` = False
- **并行任务**：`--parallel 1`（R9：OHOS worker 并行约束）
- **产物**：`libmailio.so`（7,358,912 字节）、头文件 `include/mailio/`、
  CMake 配置文件、pkg-config 文件（`mailio.pc`）
- **签名**：共享库使用 boost 配方的签名模式（llvm-objcopy + binary-sign-tool）

## Conan 配方关键决策

### R32 — 平台检测
`validate()` 使用 `self.settings.os not in ("Linux", "OHOS")` — 正确，
而非 `== "Linux"`。

### R33 — build() 中不使用 shell 环境变量
所有编译器标志来自 `CMakeToolchain` / `CMakeDeps`，不使用 `${CC}`、
`${CFLAGS}` 等 shell 变量。

### R34 — 实质性测试
`test_package/test.cpp` 构造 `mailio::message` 对象，设置 from/recipient/
subject/content，调用 `format()` 生成 MIME 字符串，并验证关键头部和
内容存在。覆盖了 MIME 格式化代码路径（message.cpp、mime.cpp、
base64.cpp、codec.cpp 等）。

### R38 — 库类型，非命令行工具
mailio 只产出 `libmailio.so`（无可执行文件），不需要 `commands.json`。

### R39 — 官方源码 URL
`conandata.yml` 使用 GitHub 官方 tag 归档 URL。CI 脚本会自动为
GitHub 不可达的环境（如 OHOS）添加镜像 fallback URL。

## 已知限制

- 上游测试（`MAILIO_BUILD_TESTS`）需要实时邮件服务器连接，在 Conan
  配方中已禁用。test_package 提供离线 API 验证作为替代。
- IMAP 文件夹操作仅支持 ASCII 文件夹名（上游限制）。
- 不支持异步 I/O（上游限制）。

## 本地验证历史

| 日期 | 运行 | 结果 |
|------|------|------|
| 2026-08-04 | conan create + test_package | 通过 — "mailio test passed!" |
| 2026-08-04 | 功能测试（6/6 项） | 通过 — MIME 构造/解析/mime/地址/组/CC-BCC |
| 2026-08-04 | CI 干净构建（boost+mailio 从源码） | 通过 — L4 安全扫描通过 |
