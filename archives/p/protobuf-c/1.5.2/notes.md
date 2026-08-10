# protobuf-c 1.5.2 适配笔记

## 编译环境
- 构建系统: cmake (build-cmake/ subdirectory)
- 编译日期: 2026-08-08
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码: protobuf-c-1.5.2.tar.gz
2. 应用补丁:
   - 0001: config.guess 添加 HarmonyOS 平台检测
   - 0002: CMakeLists.txt 将 find_package(Protobuf) 移入 if(BUILD_PROTOC) 块
3. CMake 配置: `cmake ../build-cmake -DBUILD_PROTOC=OFF -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTS=OFF`
4. 编译: `make -j2`
5. Staging 安装: `make install DESTDIR=$TEST_PREFIX`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Autotools config.status 报 "Permission denied" | HarmonyOS 文件系统限制, config.status 创建临时子目录失败 | 改用 CMake 构建系统 (build-cmake/ 子目录) |
| 2 | CMake 无条件要求 find_package(Protobuf) | CMakeLists.txt 在 BUILD_PROTOC 选项前调用 find_package | 补丁: 将 protobuf 查找移入 if(BUILD_PROTOC) 块 |
| 3 | protoc-gen-c 需要 protobuf (C++) | protobuf 未发布到 ohpcd 制品仓 | BUILD_PROTOC=OFF, 仅构建 C 运行时库 |

## 源码修改

- 0001-build-aux-config.guess.patch: 添加 HarmonyOS 平台检测 (config.guess)
- 0002-build-cmake-CMakeLists.txt.patch: 使 protobuf 查找条件化于 BUILD_PROTOC 选项

## 依赖版本

无运行时依赖。protoc-gen-c 需要 protobuf/33.6 (未发布)。

## 验证结果

```bash
cmake ../build-cmake -DBUILD_PROTOC=OFF -DBUILD_SHARED_LIBS=OFF
make -j2
# 结果: libprotobuf-c.a (33344 bytes)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libprotobuf-c.a | 33344 | 静态库 |
| protobuf-c.h | - | 公共头文件 |
| libprotobuf-c.pc | - | pkg-config 文件 |
| cmake config files | - | CMake 配置文件 |

## 注意事项

- protoc-gen-c (代码生成器) 未构建, 因为 protobuf/33.6 未发布到 ohpcd 制品仓
- conanfile.py 提供 build_protoc 选项, 当 protobuf 可用时可启用
- Autotools 构建系统在 HarmonyOS 上不可用 (config.status 权限问题), 使用 CMake 替代
---

**编译结束**: 2026-08-08 02:08
**最终状态**: built
