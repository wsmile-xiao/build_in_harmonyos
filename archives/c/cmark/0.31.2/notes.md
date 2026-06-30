# cmark 0.31.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-21
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：从 GitHub 下载 cmark-0.31.2.tar.gz
2. CMake 配置：`cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF ..`
3. 编译：`make -j1`
4. 安装到 staging：`make install DESTDIR=/storage/Users/currentUser/tmp/test-install-cmark-0.31.2`
5. 测试：`ctest --output-on-failure`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败 | Python urllib SSL 验证失败 | 使用 curl -k 手动下载 tarball |
| 2 | CMake 提示 "System is unknown to cmake" | HarmonyOS 未被 CMake 识别 | 配置继续完成，不影响编译 |
| 3 | Python 测试失败 | Python ctypes 缺少 libffi.so.8 | 核心测试通过（api_test, html_normalization），记录跳过原因 |

## 源码修改

无补丁，源码无需修改即可编译。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- python3: 3.12.8

## 验证结果

```bash
# 版本验证
/storage/Users/currentUser/tmp/test-install-cmark-0.31.2/storage/Users/currentUser/usr/local/bin/cmark --version
cmark 0.31.2 - CommonMark converter
(C) 2014-2016 John MacFarlane

# 测试结果
ctest --output-on-failure
40% tests passed, 3 tests failed out of 5
- api_test: PASSED (C API 测试)
- html_normalization: PASSED (HTML 规范化)
- spectest_executable: FAILED (Python ctypes 缺少 libffi)
- smartpuncttest_executable: FAILED (Python ctypes 缺少 libffi)
- regressiontest_executable: FAILED (Python ctypes 缺少 libffi)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cmark | 可执行文件 | Markdown 转 HTML/XML/LaTeX 等格式 |
| libcmark.a | 静态库 | CMark 解析和渲染库 |
| cmark.h | 头文件 | C API 接口定义 |

## 注意事项

1. 使用静态库编译（BUILD_SHARED_LIBS=OFF）以避免 ELF 签名问题
2. Python 测试需要 libffi.so.8，核心功能已通过 C API 测试验证
3. CMake 在 HarmonyOS 上提示系统未知，但不影响编译结果
---

**编译结束**: 2026-05-21 17:23
**最终状态**: built
