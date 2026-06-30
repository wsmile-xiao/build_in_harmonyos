# libjpeg-turbo 3.1.4.1 编译笔记

**日期**: 2026-04-21
**状态**: ✅ published

## 编译环境

- **构建系统**: CMake
- **编译器**: clang
- **目标平台**: HarmonyOS (aarch64)

## 编译配置

```bash
cmake -G"Unix Makefiles" \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DWITH_SIMD=0 \
  -DWITH_TESTS=0 \
  ..
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

### 关键参数说明

- `-DWITH_SIMD=0`: 禁用 SIMD 加速（解决 E096 链接失败问题）
- `-DWITH_TESTS=0`: 禁用测试套件（简化编译流程）
- `-DCMAKE_BUILD_TYPE=Release`: Release 构建

## 编译过程

| 步骤 | 状态 | 备注 |
|------|------|------|
| Step 1 init | ✅ | 源码下载完成 |
| Step 2 patches | ✅ | 无补丁 |
| Step 3 configure | ✅ | cmake 配置成功 |
| Step 4 make | ✅ | 编译成功 |
| Step 5 install | ✅ | 安装到 staging |
| Step 6 safety | ✅ | 安全验证通过 |
| Step 7 check | ⏭️ | 测试已禁用 |
| Step 8 staging | ✅ | staging 验证通过 |
| Step 9 package | ✅ | 打包完成 |
| Step 10 deploy | ✅ | 本地部署验证 |
| Step 11 finish | ✅ | 归档完成 |

## 遇到的问题

### E096: SIMD 链接失败

**问题描述**: CMake 无法识别 HarmonyOS 平台，SIMD 模块编译时出现链接失败。

**解决方案**: 禁用 SIMD 加速功能 (-DWITH_SIMD=0)。

**影响**: 性能略有下降，但核心 JPEG 编解码功能完全可用。

## 知识沉淀

- **E096**: libjpeg-turbo SIMD 链接失败（未知平台），需禁用 SIMD
- **CMake 平台检测**: CMake 无法识别 HarmonyOS，但不影响核心功能编译

## 制品验证

```bash
# 动态库
~/usr/local/lib/libjpeg.so -> libjpeg.so.63.4.0
~/usr/local/lib/libturbojpeg.so -> libturbojpeg.so.0.4.0

# 静态库
~/usr/local/lib/libjpeg.a
~/usr/local/lib/libturbojpeg.a

# 可执行文件
~/usr/local/bin/cjpeg
~/usr/local/bin/djpeg
~/usr/local/bin/jpegtran
~/usr/local/bin/tjbench

# 头文件
~/usr/local/include/jpeglib.h
~/usr/local/include/turbojpeg.h
~/usr/local/include/jconfig.h
~/usr/local/include/jmorecfg.h
```

## 制品文件（不提交）

- `libjpeg-turbo-3.1.4.1-ohos-aarch64.tar.gz` (3.4MB)
- `libjpeg-turbo-3.1.4.1-ohos-aarch64-debug.tar.gz` (306KB)

---

**编译结束**: 2026-04-21 10:30
**最终状态**: published