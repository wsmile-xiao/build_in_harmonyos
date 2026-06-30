# bento4 1.6.0-641 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 从 GitHub 克隆源码：
   ```bash
   git clone --depth 1 --branch v1.6.0-641 https://github.com/axiomatic-systems/Bento4.git
   ```

2. 创建 build 目录并配置 CMake：
   ```bash
   mkdir build && cd build
   cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$HOME/usr/local ..
   ```

3. 编译：
   ```bash
   make -j2
   ```

4. 安装到 staging 目录：
   ```bash
   make install DESTDIR=$HOME/tmp/test-install-bento4-1.6.0-641
   ```

5. 安装到本地验证：
   ```bash
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 报 "System is unknown to cmake" | HarmonyOS 平台未被 CMake识别 | 无需处理，编译正常完成 |

## 源码修改

无需修改源码，原生支持。

## 依赖版本

- cmake (系统自带)
- clang 15.0.4
- 无外部依赖

## 验证结果

```bash
$ ~/usr/local/bin/mp4info
MP4 File Info - Version 1.3.4
(Bento4 Version 1.6.0.0)
(c) 2002-2017 Axiomatic Systems, LLC
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libap4.a | 22M | 静态库 |
| mp4info等 | 各约1M | 26个命令行工具 |

## 注意事项

- Bento4 无外部依赖，全自包含
- 静态库体积较大（22M），未 strip
- 需要后续 ELF 签名才能在鸿蒙上执行
---

**编译结束**: 2026-05-26 20:06
**最终状态**: built
