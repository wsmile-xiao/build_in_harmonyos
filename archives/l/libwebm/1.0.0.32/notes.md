# libwebm 1.0.0.32 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-03
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `python3 $SKILL_ROOT/scripts/ohc-run.py init-build libwebm 1.0.0.32 --url=...`（手动下载源码包后放入 ~/tmp/builds/）
2. `mkdir _cmake_build && cd _cmake_build`
3. `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXE_LINKER_FLAGS="-fuse-ld=bfd" -DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=bfd"`
4. `make -j1`
5. `make install DESTDIR=$TEST_PREFIX`
6. `make install`（不带 DESTDIR，安装到 $DEFAULT_PREFIX）
7. `python3 $SKILL_ROOT/scripts/ohc-run.py verify-build libwebm 1.0.0.32`
8. `python3 $SKILL_ROOT/scripts/ohc-run.py package libwebm 1.0.0.32`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub下载失败（SSL/超时） | 鸿蒙环境无法直接访问GitHub | 使用 gh-proxy.com 镜像手动下载后放入 ~/tmp/builds/ |
| 2 | cmake build目录冲突源码的build/子目录 | 源码自带build/子目录存放cmake模块，创建同名build输出目录会覆盖它 | 使用 `_cmake_build` 作为cmake输出目录名避免冲突 |
| 3 | 可执行文件权限被拒 | HarmonyOS ELF签名要求 | 使用 ohc-run.py sign-elf 签名后可正常执行 |
| 4 | manifest.yaml缺少build_system字段 | 模板默认为autotools | 手动修正为cmake并添加build_system字段 |
| 5 | cmake检测平台为HarmonyOS（unknown） | cmake无HarmonyOS平台定义 | 不影响编译，cmake自动跳过平台相关检查 |

## 源码修改

无补丁，源码无需修改即可在鸿蒙平台编译。

## 依赖版本

无外部依赖（libwebm是纯C++库，无必需依赖）。

## 验证结果

```bash
# Staging目录产物检查
$ ls $DEFAULT_PREFIX/lib/libwebm.a
libwebm.a  (357458 bytes, ar archive)

# 可执行文件验证（签名后）
$ ./webm_info --help
Usage: webm_info [options] -i input
  -h | -?               show help
  -v                    show version

# 质量门禁
G1 Binary Integrity: PASS
G2 Functional: PASS (⚠️1 - 纯库项目无bin可执行文件，此为预期)
G3 Portability: PASS
G4 Archive: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libwebm-1.0.0.32-ohos-aarch64.tar.gz | 571KB | 预编译包（含libwebm.a + 17个头文件） |

## 注意事项

- 源码目录包含build/子目录（存放cmake模块cxx_flags.cmake/msvc_runtime.cmake），cmake输出目录不能命名为build，需用其他名称如_cmake_build
- libwebm是纯静态库项目，只安装libwebm.a和头文件，无bin可执行文件（但编译过程生成7个示例工具）
- cmake会检测到HarmonyOS为未知平台，不影响编译结果
---

**编译结束**: 2026-06-04 15:14
**最终状态**: published
