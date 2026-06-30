# wireshark 4.4.16 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-05-25
- 编译器: clang/clang++
- 状态: failed

## 编译步骤

### 1. 源码下载
```bash
# 从官方下载源码包（SSL 证书验证失败）
# 问题：Wireshark 官方网站 SSL 证书验证失败
# 解决：使用 curl -k 跳过证书验证手动下载
curl -k -L -O https://www.wireshark.org/download/src/wireshark-4.4.16.tar.xz

# 本地存储位置
/storage/Users/currentUser/tmp/sources/wireshark-4.4.16.tar.xz

# SHA256 校验和
0bda0e34a4c5da72ea9009134d733783d08189c07462198e53a4f533fd1201fd
```

### 2. 源码解压
```bash
# 解压到构建目录
tar -xf /storage/Users/currentUser/tmp/sources/wireshark-4.4.16.tar.xz
# 源码目录: /storage/Users/currentUser/builds/wireshark-4.4.16.orig
# 工作目录: /storage/Users/currentUser/builds/wireshark-4.4.16.work
```

### 3. CMake 配置
```bash
# 创建构建目录
mkdir -p /storage/Users/currentUser/builds/wireshark-4.4.16.work/build
cd /storage/Users/currentUser/builds/wireshark-4.4.16.work/build

# CMake 配置命令
cmake /storage/Users/currentUser/builds/wireshark-4.4.16.work \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_C_COMPILER=clang \
      -DCMAKE_CXX_COMPILER=clang++

# 配置失败，错误信息：
# CMake Error: Could NOT find GLIB2 (missing: GLIB2_LIBRARY GLIB2_MAIN_INCLUDE_DIR)
# Wireshark requires GLib 2.x >= 2.50.0
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败 | Wireshark 官方网站 SSL 证书链不完整或过期 | 使用 `curl -k` 跳过证书验证下载源码包 |
| 2 | GLib 未找到 | 系统未安装 GLib 开发包，且预编译库中无 GLib | 需要先编译 GLib 2.x (>= 2.50.0) |
| 3 | 构建系统误判 | 初步判断为 autotools，实际为 CMake | 修正 manifest.yaml 中的 build.system |

## 依赖发现过程

### 初步分析
1. 查看 README.md 和 INSTALL 文件，确认依赖：
   - GLib 2.x >= 2.50.0 (必需)
   - libpcap (必需，用于捕获)
   - Qt >= 5.9 (可选，用于 GUI)
   - Python 3 (构建依赖)
   - flex (构建依赖)

### CMake 配置检查
```bash
# 检查 CMakeCache.txt 中的依赖状态
grep "GLIB2" /storage/Users/currentUser/builds/wireshark-4.4.16.work/build/CMakeCache.txt

# 结果：
# GLIB2_INTERNAL_INCLUDE_DIR:PATH=GLIB2_INTERNAL_INCLUDE_DIR-NOTFOUND
# GLIB2_LIBRARY:FILEPATH=GLIB2_LIBRARY-NOTFOUND
# GLIB2_MAIN_INCLUDE_DIR:PATH=GLIB2_MAIN_INCLUDE_DIR-NOTFOUND
```

### 依赖清单
根据编译失败分析，确认以下依赖关系：

**必需依赖**（尚未预编译）：
- glib/2.x (>= 2.50.0) - **缺失，导致编译失败**
- libpcap/x.x
- libgcrypt/x.x

**构建依赖**：
- cmake >= 3.5
- python3
- flex

**可选依赖**：
- qt >= 5.9 (GUI)
- zlib (压缩支持)
- lz4 (压缩支持)
- zstd (压缩支持)

## 源码修改
无补丁文件。编译在配置阶段失败，未进行源码修改。

## 验证结果
```bash
# 编译状态检查
# cmake 配置失败，未生成 Makefile 或 build.ninja
# 无法进行后续编译和验证

# 预期的验证命令（编译成功后）
tshark --version
tshark -D  # 列出捕获接口
```

## 交付物
无。编译在配置阶段失败，未生成可执行文件。

## 下一步行动
1. **优先级 P0**: 编译 GLib 2.x 依赖库
2. **优先级 P1**: 编译 libpcap 依赖库
3. **优先级 P1**: 编译 libgcrypt 依赖库（如需要）
4. **优先级 P2**: 重新尝试编译 Wireshark（仅命令行工具）
5. **优先级 P3**: 编译 Qt 依赖（如需要 GUI 版本）

## 注意事项
1. Wireshark 4.4.x 系列要求 GLib >= 2.50.0，较旧系统可能需要升级 GLib
2. 官方下载站点存在 SSL 证书问题，建议使用镜像站或手动下载
3. TShark（命令行版本）可独立编译，不依赖 Qt
4. 数据包捕获功能需要特殊权限配置

---
**编译结束**: 2026-05-25 16:43
**最终状态**: failed
**失败阶段**: CMake 配置
**失败原因**: 缺少 GLib 2.0 (>= 2.50.0) 依赖