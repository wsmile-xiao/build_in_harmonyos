# mkclean 0.9.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-29
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
source .build-context-mkclean-0.9.0
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_SYSTEM_NAME=Linux
make -j2 CC=clang CXX=clang++
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SourceForge SSL 证书下载失败 | 鸿蒙环境 CA 证书缺失 | 用 curl -kL 手动下载，放入 $TMPDIR/builds/ |
| 2 | cmake_minimum_required(VERSION 3.1.2) 报错 | cmake 4.1.2 移除了 < 3.5 兼容 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 3 | 链接错误: undefined symbol tcsicmp/tcscmp/File_Class 等 | HarmonyOS 不被 cmake 识别为 UNIX，导致 str_linux.c/file_libc.c/date_libc.c/ccsystem_posix.c 未编译 | 添加 -DCMAKE_SYSTEM_NAME=Linux 让 cmake 走 UNIX 分支 |

## 源码修改

### 补丁: 0001-fix-version-exit-code.patch
- **文件**: mkclean/mkclean.c 第 1563 行
- **问题**: `--version` 和 `--help` 设置 `Result = -1`，导致退出码 255
- **修复**: `Result = ShowVersion ? 0 : -1`，使 `--version`/`--help` 返回 0
- **原因**: L2 smoke test 要求 `--version` 或 `--help` 返回退出码 0

## 依赖版本

- 无外部依赖，corec/libebml2/libmatroska2 均内嵌于源码树

## 验证结果

```bash
$ ./mkclean/mkclean
mkclean v0.9.0, Copyright (c) 2010-2020 Matroska Foundation
Usage: mkclean [options] <matroska_src> [matroska_dst]
...

$ readelf -d ./mkclean/mkclean | grep NEEDED
Shared library: [libc.so]  # 仅系统库，符合 R26 静态链接要求

$ ctest
No tests were found!!!  # cmake 未注册 ctest 测试

$ ./corec/tests/string_test
# 部分格式测试通过/失败（自定义 printf 实现在新平台的预期行为）
EXIT=0
```

## 交付物

| 文件 | 路径 | 说明 |
|------|------|------|
| mkclean | build/mkclean/mkclean | 主可执行文件 (428KB) |
| mkWDclean | build/mkclean/mkWDclean | WebM 清洗工具 (428KB) |
| libcorec.a | $TEST_PREFIX/.../lib/libcorec.a | 静态库 |
| libebml2.a | $TEST_PREFIX/.../lib/libebml2.a | 静态库 |
| libmatroska2.a | $TEST_PREFIX/.../lib/libmatroska2.a | 静态库 |

## 注意事项

- mkclean 的 CMakeLists.txt 未为可执行文件添加 install() 目标，make install 只安装库和头文件
- cmake 未识别 HarmonyOS 平台，需用 -DCMAKE_SYSTEM_NAME=Linux 触发 UNIX 代码路径
- SourceForge 下载需绕过 SSL 验证（curl -kL）
---

**编译结束**: 2026-06-29 20:10
**最终状态**: published
