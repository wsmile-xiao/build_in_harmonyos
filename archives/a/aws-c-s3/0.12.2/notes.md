# aws-c-s3 0.12.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang 15 (OHOS aarch64)
- 状态: built (conan recipe verified)

## 依赖链（全部使用制品仓已发布版本）
```
aws-c-s3 0.12.2
├─ aws-c-auth 0.10.4
├─ aws-checksums 0.2.10
├─ aws-c-common 0.14.3
├─ aws-c-cal 0.9.15 → aws-lc 5.4.0
├─ aws-c-io 0.27.5
├─ aws-c-http 0.11.0
└─ aws-c-sdkutils 0.2.7
   (aws-c-compression 0.3.2 经 aws-c-http 传递引入)
```

## 关键适配点
1. **CMAKE_PREFIX_PATH 替代 CMakeDeps**：aws-c-common 的 cmake config 会创建
   `AWS::aws-c-common` 目标并把 Aws*.cmake 模块加入 CMAKE_MODULE_PATH；CMakeDeps
   生成器会改写目标名导致构建失败。build() 中收集全部依赖的 package_folder 注入
   CMAKE_PREFIX_PATH，让 find_package 使用原始 config 文件。
2. **Threads 补丁**：`aws_use_package(aws-c-auth)` 展开的依赖链接需要
   Threads::Threads，上游 CMakeLists 缺少 find_package(Threads REQUIRED)，
   补丁在 aws_use_package 前插入。
3. **aws-lc 直依赖**：aws-c-cal 的 Findcrypto.cmake 需要 libcrypto 路径，
   将 aws-lc 声明为直依赖让 toolchain 注入其 lib/include 路径。
4. **测试运行时问题**（test_package 内解决，不修改依赖包）：
   - aws-c-http 引用 aws_tls_handler_protocol，而 aws-c-io (BYO_CRYPTO=ON)
     未编译该符号 → test_package 提供 stub.c + `--export-dynamic` +
     `--allow-shlib-undefined`；
   - 制品仓 .so 无 SONAME（上游 CMake 未设置 SOVERSION），消费方 NEEDED
     为绝对路径 → test() 中扫描 NEEDED 并在不存在的路径建 symlink，
     再以 LD_LIBRARY_PATH 运行测试二进制。

## 上游测试说明
上游 tests/ 需要 cmake test framework 与预配置 mock server
(ENABLE_MOCK_SERVER_TESTS)，交叉编译 CI 环境不可运行，BUILD_TESTING=OFF。
test_package 从消费者视角验证 aws_s3_library_init /
aws_s3_get_current_platform_info / aws_s3_library_clean_up。

## 交付物
conanfile.py, conandata.yml, patches/, test_package/
