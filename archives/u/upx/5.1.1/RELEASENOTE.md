# UPX 5.1.1 发布说明

**发布日期:** 2026-05-13  
**平台:** HarmonyOS (HongMeng Kernel 1.12.0) aarch64  
**编译器:** Clang 15.0.4  

---

## 概述

UPX (Ultimate Packer for eXecutables) 是一个开源、高性能的可执行文件压缩工具。本次发布为 HarmonyOS aarch64 平台的预编译版本。

---

## 版本信息

- **软件名称:** UPX
- **版本:** 5.1.1
- **源码来源:** upx-5.1.1-src.tar.xz
- **构建系统:** CMake

---

## 嵌入的库版本

- UCL data compression library 1.03
- zlib data compression library 1.3.1.1-motley
- LZMA SDK version 4.43
- doctest C++ testing framework version 2.4.11

---

## 编译配置

```bash
CXXFLAGS="-stdlib=libc++"
LDFLAGS="-lc++"
cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
make -j$(nproc)
```

---

## 功能支持

- ✅ Linux ELF (arm64) 格式压缩/解压
- ✅ 命令行参数 (--help, --version, --license, --sysinfo)
- ✅ 压缩级别选项 (-1 到 -9, --best)
- ✅ 解压功能 (-d)
- ✅ 文件信息显示 (--fileinfo)

---

## 测试结果

| 测试项 | 结果 |
|--------|------|
| 版本信息显示 | ✅ 通过 |
| 帮助信息 | ✅ 通过 |
| 许可证信息 | ✅ 通过 |
| 系统信息 | ✅ 通过 |
| ELF 压缩 | ✅ 通过 (49% 压缩率) |
| ELF 解压 | ✅ 通过 |

---

## 包内容

- `upx-5.1.1-ohos-aarch64.tar.gz` - 主发布包 (3.28MB)
- `upx-5.1.1-ohos-aarch64-debug.tar.gz` - 调试符号包 (371KB)
- `install-upx-5.1.1.sh` - 安装脚本

---

## 安装方法

```bash
# 方法1: 使用安装脚本
tar -xzf upx-5.1.1-ohos-aarch64.tar.gz
cd pkg-upx-5.1.1
./install-upx-5.1.1.sh

# 方法2: 手动安装
tar -xzf upx-5.1.1-ohos-aarch64.tar.gz
cp pkg-upx-5.1.1/bin/upx /usr/local/bin/
```

---

## 许可证

UPX 采用双重许可证:
- GPLv2+ (开源使用)
- 商业许可证 (需要特殊许可)

---

## 已知限制

1. 不支持压缩 HarmonyOS 特有的可执行格式
2. 需要链接 libc++ 标准库
3. 当前为 partial 状态，需要补充完整测试流程

---

## 贡献者

- Markus Franz Xaver Johannes Oberhumer (原作者)
- Laszlo Molnar
- John F. Reiser
- HarmonyOS 适配: OpenDesk 编译框架