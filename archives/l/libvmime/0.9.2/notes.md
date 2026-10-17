# libvmime 0.9.2 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists 2.8.6 时代，C++03/11 混合）
- 编译日期: 2026-09-18
- 编译器: clang/clang++ 15.0.4（OHOS aarch64，conan profile ohos-aarch64）
- 状态: built（conan-verify W3 全绿：G0–G4、L2、L4、L5 PASS）
- worktree: ~/qzy/GLM-50-libvmime-0.9.2（分支 feat/libvmime-0.9.2，基于 upstream/main）
- CONAN_HOME: ~/tmp/ch/home-glm50-libvmime

## 编译步骤

1. `ohc-run.py init-build libvmime 0.9.2 --auto --url <官方 GitHub archive>`：下载源码（SHA256 9874bf91…）、建归档骨架。
2. 探雷迭代修兼容性（CMake 4/musl），生成 7 个补丁（见 manifest patches_applied）。
3. conanfile.py：cppunit test_requires + build() 内 TMPDIR 设置 + cmake.test() 受控执行。
4. `ohc-run.py conan-verify libvmime 0.9.2`：conan create 全链路通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure FATAL：CMake <3.5 兼容已移除 | 上游 cmake_minimum_required(VERSION 2.8.6)；自带 cmake-cxx11 模块同样 2.8.3 | 补丁提升至 3.10（主 CMakeLists + CheckCXX11Features.cmake 两处） |
| 2 | No charset conversion library was selected/found | 自带 FindIconv 用 FIND_LIBRARY(iconv libiconv … c) 找独立库；musl 的 iconv 在 libc 内，无独立库 | 补丁改 FindIconv.cmake 为 libc 内置探测，保留 ICONV_SECOND_ARGUMENT_IS_CONST 编译检查（musl 非 const 自适应） |
| 3 | getaddrinfo_a 探测连带 gnutls NOTFOUND 崩 | GNUTLS_LIBRARY=NOTFOUND 泄漏进 CMAKE_REQUIRED_LIBRARIES，污染后续 try_compile | 补丁在 gnutls/anl 探测后显式清空 CMAKE_REQUIRED_LIBRARIES/DEFINITIONS |
| 4 | posixSocket.cpp strerror_r 二义性编译错 | 宏判定 `(_POSIX_C_SOURCE>=200112L)&&!_GNU_SOURCE` 在 musl+_GNU_SOURCE 下选错 GNU 分支（musl 实为 XSI 语义） | 补丁改按 `defined(__GLIBC__)` 选择分支：glibc 走 GNU 返回值、其余走 XSI |
| 5 | pthread 探测失败 → VMIME_HAVE_PTHREAD=0 → PLockHelper 未定义 | musl 的 pthread 在 libc 内，无独立 libpthread | 补丁 FIND_LIBRARY 失败时 CHECK_FUNCTION_EXISTS(pthread_mutex_lock) 兜底置 PTHREAD_LIB=c |
| 6 | encoding.cpp bind2nd 编译错 | C++17 移除 std::bind2nd（toolchain 默认 gnu++17） | 补丁替换为 lambda |
| 7 | generate 失败：target "vmime" 不存在（run-tests/测试） | tests 段链接目标写死共享库名；静态-only 构建只有 vmime-static | 补丁按 VMIME_BUILD_SHARED_LIBRARY 自适应选 VMIME_TESTS_LINK_LIBRARY（链接+依赖 4 处） |
| 8 | 静态构建 fatal error: vmime/export-shared.hpp not found | export.hpp 无条件 include export-shared.hpp，而该头仅在共享库构建时生成 | 补丁静态-only 分支用 export-static.hpp 内容复制生成 export-shared.hpp |
| 9 | fileContent/maildir 测试 filesystem_exception | 测试向硬编码 /tmp 写临时数据，设备 /tmp 只读 | 补丁改用 getenv(TMPDIR) 兜底；conanfile build() 设 os.environ["TMPDIR"]=build 目录 |
| 10 | TLS/SASL 段把 NOTFOUND include 路径写进 target | 上游 OPTION 默认 ON 且探测失败无守卫（0.9.2 已知缺陷，0.9.3 修复） | 配方显式 VMIME_HAVE_TLS_SUPPORT/SASL=OFF（OHOS 无 gnutls/gsasl，可选特性诚实裁剪） |

## 源码修改（补丁清单）

见 manifest.yaml patches_applied：CMakeLists（CMake4 兼容+泄漏清理+pthread 兜底+tests 自适应链接）、FindIconv（libc 内置）、CheckCXX11Features（版本）、posixSocket（strerror_r XSI 分支）、encoding（bind2nd→lambda）、fileContentHandlerTest/maildirStoreTest（TMPDIR）。无平台宏空壳；均为构建基础设施与 POSIX 便携性修复。

## 依赖版本

- cppunit/1.15.1（test_requires，仅构建期上游测试用，不入下游依赖闭包）
- 库本体零强制外部依赖（TLS/SASL 特性在 OHOS 上裁剪；charset 走 libc iconv）

## 验证结果

```bash
# conan create（conan-verify 内部执行，profile ohos-aarch64）
# ctest：54/58 可执行通过（93.1%）；用例口径 445/453 CPPUNIT 用例通过（98.2%）
# 消费者测试：libvmime consumer test PASS
# 失败 4 个可执行共 8 个用例，全部为平台能力限制，逐项申报见 test-report.md
```

## 测试账本（五维）

- N_static（上游静态用例数）：453 —— VMIME_TEST 宏（CPPUNIT_TEST 映射）逐条计数，tests/ 共 58 个测试文件
- N_registered：58+1（58 个逐测试可执行 + run-tests 聚合，均 ADD_TEST 注册）
- N_executed（实际执行）：445 通过 / 8 失败（真实执行，失败逐项申报非跳过）
- 未执行分类数：0（全部执行；无跳过）
- N_consumer：1 个程序 test_libvmime（messageBuilder 构造+generate+RFC822 头断言，2 断言全过）

### 失败 8 用例逐项申报

| 用例 | 数量 | 技术原因 |
|------|------|----------|
| charsetTest::testUTF7Support、IMAPUtilsTest::testFromModifiedUTF7、testStringToPath | 3 | musl libc 的 iconv 不含 UTF-7/Modified-UTF-7 转换器，iconv_open 直接失败（"Cannot initialize converter"）；桌面 glibc iconv 支持 UTF-7 故上游在 Linux 可过 |
| maildirStoreTest 的 KMail/Courier list/rename/destroy 系列用例 | 4 | 同为 UTF-7 转换依赖（maildir 目录名转 IMAP modified-UTF-7），非文件系统问题（TMPDIR 修复后剩余） |
| POP3StoreTest::testCreateFromURL | 1 | POP3S 组件随 TLS 特性裁剪未编译（OHOS 无 gnutls/openssl；上游用例假设 TLS 可用） |

## 路径 A/B/C 判断

- 判定：纯路径 A。
- 理由：CMake4 兼容与 musl iconv 差异为通用便携性知识，知识库已有同类条目（E 系 CMake4/musl 适配先例），本次无超出既有条目的新增可复用知识；不满足路径 B 证据门槛。
---

**编译结束**: 2026-09-18 06:58
**最终状态**: built
