# googletest 1.15.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built

## 编译步骤

### Phase 1: 初始化 (自动)
1. 下载源码: `git clone --depth 1 --branch v1.15.2 https://github.com/google/googletest.git`
2. 打包为 tar.gz: `tar czf googletest-1.15.2.tar.gz`
3. 初始化归档: `ohc-run.py init-build googletest 1.15.2 --url=file://...`

### Phase 2: 配置与编译
1. cmake 配置:
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release ..
   ```
2. 编译: `make -j1` (编译耗时约 15 秒)
3. 安装: `make install DESTDIR=/storage/Users/currentUser/test-install-googletest-1.15.2`

### Phase 3: 验证与打包
1. Staging 验证通过
2. 打包产物: `googletest-1.15.2-ohos-aarch64.tar.gz` (2183KB)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | GitHub HTTPS 证书问题 | 使用 git clone 获取源码，打包后用 file:// URL 初始化 |
| 2 | cmake 平台不识别 | HarmonyOS 未在 cmake 平台列表中 | cmake 自动检测为 Clang，无需额外配置 |

## 源码修改

无补丁。googletest 是纯 C++ 库，使用 cmake 构建，在 HarmonyOS 上无需平台适配。

## 依赖版本

无外部依赖。googletest 是自包含的测试框架库。

## 验证结果

```bash
# 编译成功，生成静态库
ls /storage/Users/currentUser/usr/local/lib/libgtest*.a
libgtest.a libgtest_main.a libgmock.a libgmock_main.a

# 头文件安装
ls /storage/Users/currentUser/usr/local/include/gtest/
gtest.h gtest-assertion-result.h gtest-death-test.h ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| googletest-1.15.2-ohos-aarch64.tar.gz | 2183KB | 预编译包（静态库 + 头文件） |

## 注意事项

1. googletest 仅提供静态库（.a 文件），无动态库
2. 使用时需链接 libgtest.a 和 libgtest_main.a
3. cmake 自动检测 HarmonyOS 平台为 "unknown"，但不影响编译
---

**编译结束**: 2026-05-27 11:23
**最终状态**: published
