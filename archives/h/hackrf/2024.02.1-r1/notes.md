# hackrf 2024.02.1-r1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码下载: https://github.com/greatscottgadgets/hackrf/archive/refs/tags/v2024.02.1.tar.gz
2. 解压到 `$TMPDIR/builds/hackrf-2024.02.1-r1.orig/` 和 `.work/`
3. 进入 `host/` 子目录（主要代码在此）
4. CMake 配置:
   ```bash
   cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
            -DLIBUSB_INCLUDE_DIR=$HOME/usr/local/include/libusb-1.0 \
            -DLIBUSB_LIBRARIES=$HOME/usr/local/lib/libusb-1.0.so \
            -DCMAKE_INSTALL_RPATH=$HOME/usr/local/lib \
            -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
   ```
5. 编译: `make -j2`
6. 修复 RPATH: 使用 patchelf 修复工具二进制的库依赖路径
7. ELF 签名: 使用 ohc-run.py sign-elf 签名所有二进制文件
8. 安装到 staging 目录并创建预编译包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 版本兼容性 | CMakeLists.txt 使用旧版语法 | 添加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | FFTW 缺失 | hackrf_sweep 需要 FFTW 库 | 修改 CMakeLists.txt 使 FFTW 可选，跳过 hackrf_sweep |
| 3 | 系统识别问题 | CMake 不识别 HarmonyOS | 使用手动配置参数，忽略警告 |
| 4 | RPATH 不正确 | 编译时链接到相对路径 | 使用 patchelf 修复二进制 RPATH |
| 5 | ELF 签名问题 | 鸿蒙系统要求 ELF 签名 | 使用 ohc-run.py sign-elf 签名 |
| 6 | libhackrf.so 未安装 | CMake 判断非 UNIX 系统 | 手动复制库文件到安装目录 |

## 源码修改

### 0001-host-hackrf-tools-src-CMakeLists.txt.patch
- 修改 `host/hackrf-tools/src/CMakeLists.txt`
- 使 FFTW 依赖可选（从 REQUIRED 改为 QUIET）
- 只有 FFTW 存在时才构建 hackrf_sweep
- 其他工具不依赖 FFTW

## 依赖版本

- libusb: 1.0.27（已安装预编译包）
- cmake: 4.1.2
- clang: 15.0.4

## 验证结果

```bash
# 工具可运行（无硬件设备导致初始化失败）
$ hackrf_info --help
hackrf_init() failed: Other error (-1000)

$ hackrf_clock --help
hackrf_init() failed: Other error (-1000)

# 所有 8 个工具都已签名并可执行
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hackrf-2024.02.1-r1-ohos-aarch64.tar.gz | 1.3MB | 预编译包 |
| libhackrf.so | 51KB | 共享库 |
| libhackrf.a | 40KB | 静态库 |
| hackrf.h | 85KB | 头文件 |
| hackrf_transfer, hackrf_info 等 8 个工具 | 各约 150KB | 工具二进制 |

## 注意事项

- hackrf_sweep 未包含在预编译包中（需要 FFTW 库）
- 工具运行需要 HackRF 硬件设备连接
- libusb-1.0.27 必须先安装

## 知识提取

1. **CMake 未知平台处理**: 当 CMake 不识别目标平台时，使用手动配置参数绕过平台检测
2. **patchelf 修复 RPATH**: 对于编译时链接路径不正确的情况，使用 patchelf --set-rpath 和 --replace-needed 修复
3. **可选依赖处理**: 将 REQUIRED 改为 QUIET，使依赖可选，便于在不完整环境中编译

---

**编译结束**: 2026-05-25 20:36
**最终状态**: built
---

**编译结束**: 2026-08-06 17:07
**最终状态**: built
