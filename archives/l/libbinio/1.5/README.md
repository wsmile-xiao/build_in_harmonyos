# libbinio 1.5 — HarmonyOS (aarch64) 编译归档

## 软件简介

libbinio 是一个二进制 I/O 流类库，提供 C++ 接口用于读写二进制数据。
它是 AdPlug 音频播放器项目的底层依赖库。

- **主页**: https://adplug.github.io/libbinio
- **许可证**: LGPL-2.1
- **版本**: 1.5
- **源码**: https://github.com/adplug/libbinio/releases/download/libbinio-1.5/libbinio-1.5.tar.bz2

## 编译信息

| 项目 | 值 |
|------|-----|
| 目标平台 | aarch64-unknown-linux-ohos (HarmonyOS) |
| 构建系统 | autotools (configure + make) |
| 编译器 | clang 15.0.4 / clang++ 15.0.4 |
| 构建日期 | 2026-06-26 |
| 状态 | published |
| Conan 引用 | libbinio/1.5 |

## 产物

### 库文件

| 文件 | 说明 |
|------|------|
| lib/libbinio.a | 静态库 (R26: 静态链接) |
| lib/libbinio.la | libtool 归档 |
| lib/pkgconfig/libbinio.pc | pkg-config 配置文件 |

### 头文件

| 文件 | 说明 |
|------|------|
| include/libbinio/binio.h | 主头文件 |
| include/libbinio/binfile.h | 文件 I/O |
| include/libbinio/binstr.h | 字符串处理 |
| include/libbinio/binwrap.h | 包装器 |

## 平台修复

1. **config.guess/config.sub 更新 (E007)**: 替换为 automake-1.17 版本，添加 HarmonyOS 系统检测
2. **umask 修复**: 将 configure 脚本中的 `umask 077` 替换为 `umask 022`，解决 HMDFS 文件系统权限问题

## 使用方法

### Conan 方式

```bash
conan install --requires=libbinio/1.5 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### pkg-config 方式

```bash
pkg-config --cflags libbinio  # -I<includedir>/libbinio
pkg-config --libs libbinio    # -L<libdir> -lbinio
```

## 验证结果

- 手动编译: ✅ configure + make + make install + make check 全部成功
- Conan 配方验证: ✅ 8 道门禁全部通过 (G0/G1/G2/G3/G4/L2/L4/L5)
- Conan test_package: ✅ test_libbinio 运行成功 ("test libbinio 1.5: OK")
