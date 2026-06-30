# Tesseract 5.3.3 - OpenHarmony 编译说明

## 基本信息
- **软件**: Tesseract OCR
- **版本**: 5.3.3
- **构建系统**: CMake
- **平台**: OpenHarmony aarch64

## 编译命令
```bash
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
make -j1
make install DESTDIR=/path/to/test-install
```

## 补丁说明
### 0001-simddetect.patch
修复 aarch64 平台 NEON SIMD 检测逻辑：
- 原: `#if defined(__aarch64__)` 自动启用 NEON
- 改: `#if defined(HAVE_NEON) && defined(__aarch64__)` 检查 HAVE_NEON

## 制品
| 文件 | 大小 | 说明 |
|------|------|------|
| tesseract-5.3.3-ohos-aarch64.tar.gz | 13M | 主包(已strip) |
| tesseract-5.3.3-ohos-aarch64-debug.tar.gz | 852K | debug符号 |

## 安装
```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- tesseract 5.3.3
```