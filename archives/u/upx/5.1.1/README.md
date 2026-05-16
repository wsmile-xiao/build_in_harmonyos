# upx 5.1.1 — OpenHarmony 编译记录

## 基本信息
- **软件**: UPX (Ultimate Packer for eXecutables)
- **版本**: 5.1.1
- **构建系统**: CMake
- **目标平台**: ohos-aarch64
- **编译状态**: ✅ 成功
- **编译日期**: 2026-05-13

## 功能概述
UPX 是一个开源、高性能的可执行文件压缩工具，支持多种可执行格式（ELF、PE、Mach-O 等）。

---

## 编译指导

### 编译环境要求
- Clang 15.0.4+ (支持 C++17)
- CMake 4.1.2+
- Make 4.4+

### 关键编译参数
```bash
# 必须添加以下参数解决 C++ 标准库链接问题
CXXFLAGS="-stdlib=libc++"
LDFLAGS="-lc++"
```

### 完整编译流程
```bash
source ~/.opendesk/apps/skills/resources/openharmony-compile-agent/.build-context-upx-5.1.1
cd $BUILD_SRC_DIR
mkdir build && cd build
CXXFLAGS="-stdlib=libc++" LDFLAGS="-lc++" cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX
make -j$(nproc)
make install
```

---

## 补丁清单
无补丁。UPX 5.1.1 源码可直接编译，仅需添加正确的编译参数。

---

## 已知限制

1. **CMake 平台警告**: HarmonyOS 平台未被 CMake 官方识别，会输出大量警告，但不影响编译
2. **C++ 标准库**: 必须显式链接 libc++，否则会出现 `undefined symbol: __cxa_begin_catch` 等错误
3. **格式支持**: 当前不支持压缩 HarmonyOS 特有的可执行格式，支持 linux/arm64 ELF

---

## 功能验证

### 版本信息
```
upx 5.1.1
UCL data compression library 1.03
zlib data compression library 1.3.1.1-motley
LZMA SDK version 4.43
```

### 基础测试命令
```bash
upx --version      # 显示版本
upx --help         # 显示帮助
upx --sysinfo      # 显示系统信息
upx --license      # 显示许可证
```

### ELF 压缩测试
```bash
# 创建测试文件
echo 'int main() { return 0; }' > test.c
cc -o test_binary test.c

# 压缩测试 (18752 bytes → 9188 bytes, 49% 压缩率)
upx test_binary

# 解压测试
upx -d test_binary
```

### 测试结果
| 测试项 | 结果 | 备注 |
|--------|------|------|
| 版本信息 | ✅ | 正确显示 5.1.1 |
| 帮助信息 | ✅ | 所有命令行参数正常 |
| ELF 压缩 | ✅ | 压缩率 ~49% |
| ELF 解压 | ✅ | 正常恢复 |

---

## 打包产物

| 文件 | 大小 | 说明 |
|------|------|------|
| upx-5.1.1-ohos-aarch64.tar.gz | 3.28MB | 发布包 |
| upx-5.1.1-ohos-aarch64-debug.tar.gz | 371KB | 调试符号包 |
| install-upx-5.1.1.sh | 1.4KB | 安装脚本 |

---

## 安装方法

```bash
# 使用安装脚本
tar -xzf upx-5.1.1-ohos-aarch64.tar.gz
cd pkg-upx-5.1.1
./install-upx-5.1.1.sh

# 或手动安装
cp pkg-upx-5.1.1/bin/upx /usr/local/bin/
```

---

## 嵌入的库版本
- UCL 1.03
- zlib 1.3.1.1-motley
- LZMA SDK 4.43
- doctest 2.4.11