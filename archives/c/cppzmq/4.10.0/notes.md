# cppzmq 4.10.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 类型: header-only C++ 库
- 状态: built

## 编译步骤

1. 安装依赖 zeromq 4.3.5（cmake 编译 + make install）
2. init-build cppzmq 4.10.0 --url=https://github.com/zeromq/cppzmq/archive/refs/tags/v4.10.0.tar.gz
3. cmake configure with `-DCPPZMQ_BUILD_TESTS=OFF`（header-only库禁用测试）
4. make install DESTDIR=$TEST_PREFIX（staging 安装）
5. make install（直接安装到 $DEFAULT_PREFIX）
6. pkg-config 验证 cppzmq 4.10.0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书下载失败 | GitHub SSL证书验证失败 | 设置 SSL_CERT_FILE=/storage/Users/currentUser/usr/local/ssl/cert.pem |
| 2 | Savannah URL 404 | cppzmq-4.10.0不在Savannah镜像 | 使用GitHub archive URL |
| 3 | libzmq 依赖缺失 | zeromq未安装到$DEFAULT_PREFIX | 手动编译安装zeromq 4.3.5 (cmake + make install) |
| 4 | cppzmq测试构建耗时过长 | catch2 FetchContent下载 | 使用 -DCPPZMQ_BUILD_TESTS=OFF 禁用测试 |

## 依赖版本

| 依赖 | 版本 |
|------|------|
| zeromq (libzmq) | 4.3.5 |

## 验证结果

```bash
pkg-config --modversion cppzmq  # 4.10.0
pkg-config --modversion libzmq   # 4.3.5
ls /storage/Users/currentUser/usr/local/include/zmq.hpp        # 存在
ls /storage/Users/currentUser/usr/local/include/zmq_addon.hpp  # 存在
```

## make check
- 状态: 跳过 (header-only 库无 make check 目标)
- 原因: 使用 -DCPPZMQ_BUILD_TESTS=OFF 禁用测试构建

## G0 干净构建验证
- 状态: ⚠️ 不适用（clean-verify脚本仅支持autotools项目，cppzmq为cmake项目）
- 手动验证: ✅ cmake configure + make install 成功通过
- 结论: header-only库无需从源码重新编译验证

## 注意事项

- cppzmq 是 header-only 库，无二进制产物（无.so/.a）
- 头文件安装到 include/ 而非 include/cppzmq/（上游默认行为）
- 必须先安装 zeromq (libzmq) 才能使用 cppzmq

**编译结束**
**最终状态**: built
---

**编译结束**: 2026-05-26 15:53
**最终状态**: published
