# fast-cpp-csv-parser 0.0-git20160525-9bf299c-3 适配笔记

## 适配范围

- 类型：header-only C++11，只有 `csv.h`，无 CMake/Make 构建系统和正式上游单元测试套件。
- 源码：`9bf299cefb60d0e4ba7dc79d51491595ab1b3213`，codeload 归档 SHA-256 为 `1612fb060e1529cf569ca06a84d0675d89316627c6ada8b99067f3c0ad76137a`。
- Conan 包布局：`package()` 将 `csv.h` 安装到 `include/`，无库文件和运行时依赖。

## 验证

- Windows Conan create：recipe、consumer 和 test_package 均通过，真实 CSV 解析为 2 行。
- 目标 W0：OHOS/armv8、clang 15、libc++、C++17、`os.version=6.0` 图解析通过，单节点、零依赖、`info_invalid=null`。
- 目标 W3：USB-HDC serial `3QC0124C20000792`，官方 signer 自签，AArch64 consumer 唯一 launch 返回 `rows=2`，进程和临时文件清零，release/postrelease PASS。

上游没有可计数的正式测试入口，因此保留 N/A，并以真实 consumer 验证作为包功能证据；这不替代平台 CI、AI Review 或 Pre-PR 门禁。
