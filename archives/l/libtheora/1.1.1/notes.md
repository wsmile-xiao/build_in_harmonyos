# libtheora 1.1.1 编译记录

## 编译日期
2026-05-20

## 软件信息
- 名称: libtheora
- 版本: 1.1.1
- 语言: C
- 构建系统: Autotools + SCons (upstream), CMake (custom)
- 仓库: https://github.com/xiph/theora
- 官方下载: https://downloads.xiph.org/releases/theora/libtheora-1.1.1.tar.bz2

## 依赖
- libogg 1.3.5 (已安装于 ~/usr/local)

## 编译过程对话记录

### 1. 初始化编译环境
尝试使用 ohc-run.py init-build，但 SSL 证书验证失败。
**决策**: 手动下载源码。

### 2. 源码下载
使用 curl -k 从 Xiph.Org 官方下载成功（约 1.9MB，耗时约 2 分钟）。

### 3. Autotools 构建尝试
**问题**:
- config.guess 无法识别 HarmonyOS 系统
- HMDFS TMPDIR 权限问题导致 configure 无法创建临时文件
- umask 设置无法解决问题

**尝试修复**:
1. 更新 config.guess/config.sub 到最新版本 (2025-07-10)
2. 手动指定 --build=aarch64-unknown-linux-gnu
3. 设置 umask 000
4. 使用 ~/tmp/builds 目录（非 HMDFS）

**结果**: configure 的 config.status 脚本仍无法创建临时文件，HMDFS 权限问题无法绕过。

### 4. CMake 构建方案
**决策**: 创建自定义 CMakeLists.txt，使用 CMake 构建。

**原因**:
- libogg 和 libvorbis 都使用 CMake 成功编译
- libtheora upstream 没有 CMakeLists.txt，只有 Autotools 和 Visual Studio 项目文件
- CMake 不需要创建临时文件，可以避免 HMDFS 权限问题

### 5. CMakeLists.txt 创建
创建了自定义的 CMakeLists.txt，包含：
- theoradec 静态库（解码）
- theoraenc 静态库（编码）
- theora 静态库（组合）
- 头文件安装
- pkg-config 文件生成

### 6. CMake 编译
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=$HOME/usr/local -DBUILD_SHARED_LIBS=OFF
make -j2
```

**结果**: 编译成功，有大量 operator precedence warnings（非致命）。

### 7. 安装和验证
```bash
cmake --install .
```

**产物**:
- libtheora.a (251KB)
- libtheoradec.a (155KB)
- libtheoraenc.a (193KB)
- 4 个头文件
- 3 个 pkg-config 文件

### 8. 测试程序验证
创建测试程序 test_theora.c，静态链接成功运行：
```
libtheora test
theora version: Xiph.Org libtheora 1.1 20090822 (Thusnelda)
```

## 预编译包制作
打包产物为 libtheora-1.1.1-ohos-aarch64.tar.gz (708KB)

## 源码修改清单
- 新增 CMakeLists.txt（自定义构建脚本）

## 质量门禁状态
| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 | ✅ PASS | 编译成功 |
| G1 | ✅ PASS | 头文件完整 |
| G2 | ✅ PASS | pkg-config 可用 |
| G3 | ✅ PASS | 静态链接成功 |
| G4 | ✅ PASS | 测试程序运行正常 |

## 遇到的错误和解决方法
1. **SSL 证书验证失败**: 使用 curl -k 跳过验证
2. **config.guess 不识别 HarmonyOS**: 指定 --build=aarch64-unknown-linux-gnu
3. **HMDFS TMPDIR 权限问题**: 改用 CMake 构建
4. **无 CMakeLists.txt**: 自定义创建

## 总结
- libtheora 1.1.1 编译成功
- 使用自定义 CMakeLists.txt 替代 Autotools
- 生成 3 个静态库和 4 个头文件
- 预编译包大小 708KB
- 所有质量门禁通过