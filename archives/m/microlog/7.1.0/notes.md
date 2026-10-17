# microlog 7.1.0 适配笔记

## 编译环境
- 构建系统: cmake (INTERFACE library, ulog.c 源分发) + meson (备用)
- 编译日期: 2026-09-23
- 编译器: clang/clang++ 15.0.4 (OHOS aarch64)
- 状态: published (conan-verify G0-G4 全部通过)

## 编译步骤

```bash
# 源码: 官方 tag v7.1.0 (commit 31b8f28e943d269c61c057b8e1ad30757993239c)
#   sha256: fd8aa1e993a421d90aeae5d0c9765b40f69675d1b4d117b847d3f9d940e4063b
cd $BUILD_SRC_DIR
cmake -B build-native -DCMAKE_BUILD_TYPE=Release -DULOG_BUILD_TESTS=ON \
      -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX
cmake --build build-native -j2
cmake --install build-native
cd build-native && ctest --output-on-failure
```

- conan-init 生成的 Autotools 模板与上游实际构建系统不符，重写为 CMake 配方
  (CMakeToolchain + ULOG_BUILD_TESTS=OFF + 上游自带 micrologConfig.cmake 透传,
  cmake_find_mode="none" + builddirs 指向 lib/cmake/microlog)
- conandata.yml 初始 URL 无 .tar.gz 扩展名导致 conan get() 按 zip 解压失败
  (BadZipFile)，改为官方规范 URL: https://github.com/an-dr/microlog/archive/refs/tags/v7.1.0.tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | github.com 直连超时 | 执行机无法直连 github.com:443 | codeload.github.com 官方归档主机下载，sha256 与 gh-proxy 下载字节一致 |
| 2 | init-build .work 复制失败 | 上游 example/subprojects/microlog -> ../.. 自引用符号链接环 + HMDFS 硬链接受限 | 移除 .orig 中该环链接(dev scaffolding, 非库源码)后重跑 |
| 3 | conan get() BadZipFile | conandata.yml URL 无 .tar.gz 扩展名, conan 按 zip 解压 | 改用官方规范归档 URL |
| 4 | test_package 首次失败 | test.c 调用 ulog_output_add 需 ULOG_BUILD_EXTRA_OUTPUTS 宏 | 改用默认配置真实消费者路径: ulog_info 宏 + freopen 捕获 stdout 验证输出 |
| 5 | 上游 4 个测试用例失败 | tmpfile() 返回 nullptr (详见测试台账) | 平台临时目录限制, 完整恢复尝试见台账 |

## 依赖版本
- 无第三方运行时依赖 (纯 C 标准库实现)
- 测试框架: doctest (vendored in tests/unit/doctest/doctest.h)

## 验证结果
详见 reports/upstream-test-ledger.md (双口径台账) 与 conan-verify-report.md

## 消费者验证
test_package/test.c: 仅包含公开头 <ulog.h>, 调用 ulog_info 宏(默认 stdout 输出),
freopen 捕获 stdout 并断言消息与级别字符串出现; conan create 内置 test 通过。
---

**编译结束**: 2026-09-23 04:21
**最终状态**: published
