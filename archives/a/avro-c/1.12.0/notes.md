# avro-c 1.12.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-04-24 ~ 2026-04-25
- 编译器: clang/clang++
- 状态: success

## 编译步骤
1. 使用完整 Apache Avro tarball 解压，保留 share 目录（含测试数据）
2. 应用 2 个补丁（简化版）
3. 安装依赖: jansson 2.14 + zlib 1.3.1 + snappy 1.1.10 + liblzma 5.6.2
4. `cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXE_LINKER_FLAGS=-lc++`
5. `make -j$(nproc)`
6. `make install`（DESTDIR 模式）
7. `make test` — 26/26 全部通过

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | bash 路径不标准 | OpenHarmony bash 在 /data/service/hnp/bin/bash | 补丁改为 #!/usr/bin/env bash |
| 2 | CMake SOVERSION 为空 | HarmonyOS 下 CMake 无法正确获取 | 补丁设置默认 SOVERSION |
| 3 | snappy 链接失败 | snappy 是 C++ 库 | 添加 CMAKE_EXE_LINKER_FLAGS=-lc++ |
| 4 | 测试数据路径错误 | 使用 lang/c 子 tarball 时路径不对 | 改用完整 Apache Avro tarball |

## 源码修改
- `version.sh` — bash 路径修复 (0001-version.sh.patch)
- `src/CMakeLists.txt` — SOVERSION 空值处理 (0002-src-CMakeLists.txt.patch)

## 验证结果
- make test: 26/26 全部通过 (100%)
- 质量门禁 G1-G4 全部 PASS
- 功能验证: avrocat 命令正常工作

## 交付物
| 文件 | 大小 | 说明 |
|------|------|------|
| avro-c-1.12.0-ohos-aarch64.tar.gz | 2.3MB | 预编译安装包 |

## 注意事项
- 使用完整 tarball（非 lang/c 子目录）以保留测试数据
- 所有 Codec 已启用: deflate, snappy, lzma
---

**编译结束**: 2026-08-27 15:33
**最终状态**: built
