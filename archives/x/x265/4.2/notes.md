# x265 4.2 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-20
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码（从 bitbucket master 分支 tarball）
2. 解压并设置源码目录结构
3. 在 source 目录下创建 build-linux 构建目录
4. 运行 cmake 配置：
   ```bash
   cmake -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local -DCMAKE_BUILD_TYPE=Release ../
   ```
5. 编译：`make -j$(nproc)`
6. Staging 安装：`make install DESTDIR=$TEST_PREFIX`
7. 验证安装产物
8. 本地安装：`make install`
9. 用户验证：`x265 --version`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 源码识别错误 | 脚本将 doc/reST 目录误判为源码 | 手动复制完整源码目录（包括 COPYING、source/） |
| 2 | cmake 找不到 COPYING | 源码目录结构不完整 | 复制完整 tarball 解压后的目录结构 |
| 3 | NASM 缺失警告 | 系统无 NASM 汇编器 | 无需处理，纯 C++ 编译可用 |

## 源码修改

无补丁，编译过程中未修改源码。

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4
- make: GNU Make 4.4.1

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/bin/x265 --version
x265 [info]: HEVC encoder version 4.2+3-e444744
x265 [info]: build info [Linux][clang 15.0.4][64 bit][noasm] 8bit
x265 [info]: using cpu capabilities: none!
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/x265 | 190KB | HEVC 编码器 CLI 工具 |
| lib/libx265.a | 2.4MB | 静态库 |
| lib/libx265.so | 1.9MB | 共享库 |
| include/x265.h | 113KB | API 头文件 |
| include/x265_config.h | 1.5KB | 配置头文件 |
| lib/pkgconfig/x265.pc | 309B | pkg-config 文件 |

## 注意事项

- 编译无汇编优化（NASM 缺失），性能可能较低
- cmake 检测平台为 "unknown"，但不影响编译
- 版本标识为 4.2+3-e444744（基于 git tag 4.2 后 3 个提交）
---

**编译结束**: 2026-05-20 18:17
**最终状态**: built
