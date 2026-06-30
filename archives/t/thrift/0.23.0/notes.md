# thrift 0.23.0 适配笔记

## 编译环境
- 构建系统: cmake (仅 compiler)
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: built (thrift compiler 成功，library 未编译)

## 编译步骤

由于 autotools configure 在鸿蒙平台遇到安全弹窗问题(E064)，改用 cmake 编译 thrift compiler：

1. 进入 compiler/cpp 目录
2. 创建 cmake-build 目录
3. 运行 cmake 配置：
   ```
   cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
     -DCMAKE_CXX_FLAGS="-stdlib=libc++" \
     -DCMAKE_EXE_LINKER_FLAGS="-stdlib=libc++ -lc++ -lc++abi"
   ```
4. 编译：make -j2
5. 安装：make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 卡住超时 | E064: 鸿蒙安全弹窗阻塞 conftest 执行 | 改用 cmake 编译 thrift compiler |
| 2 | 链接错误 undefined symbol | libc++ 链接缺失 | 添加 -stdlib=libc++ 和 -lc++ -lc++abi 链接选项 |

## 源码修改

无补丁，使用原生源码编译。

## 依赖版本

- flex 2.6.4
- bison 3.8.2
- cmake 4.1.2
- clang 15.0.4

## 验证结果

```bash
$ ~/usr/local/bin/thrift --version
Thrift version 0.23.0
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| thrift-0.23.0-ohos-aarch64.tar.gz | ~ | thrift compiler 预编译包 |

## 注意事项

1. 本次仅编译 thrift compiler（IDL 编译器），未编译 C++ library
2. library 部分需要 boost 依赖，但 autotools configure 在鸿蒙平台受阻
3. 后续可尝试使用 cmake 编译完整库（需要额外 cmake 模块）
---
**编译结束**: 2026-05-28 11:21
**最终状态**: built (compiler only)
---

**编译结束**: 2026-05-28 17:39
**最终状态**: built
