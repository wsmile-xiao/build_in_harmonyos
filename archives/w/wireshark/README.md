# wireshark — OpenHarmony 编译记录

## 基本信息
- 软件: wireshark
- 描述: 网络流量分析器（网络嗅探器），用于捕获和分析网络数据包
- 官网: https://www.wireshark.org
- 下载: https://www.wireshark.org/download
- 构建系统: CMake
- 目标: ohos-aarch64

## 核心组件
- **Wireshark**: 图形化网络协议分析器（需要 Qt）
- **TShark**: 命令行网络协议分析器
- **editcap**: 捕获文件编辑工具
- **capinfos**: 捕获文件信息查看工具
- **mergecap**: 捕获文件合并工具
- **text2pcap**: 文本转捕获文件工具
- **dumpcap**: 网络数据包捕获工具

## 编译依赖

### 必需依赖
- **GLib**: >= 2.50.0（核心依赖，当前缺失导致编译失败）
- **libpcap**: 网络数据包捕获库
- **Python 3**: 构建脚本依赖
- **flex**: 词法分析器生成工具
- **CMake**: >= 3.5

### 可选依赖
- **Qt**: >= 5.9（用于构建 Wireshark GUI）
- **libgcrypt**: 加密协议解析
- **libsmi**: SMI/MIB 支持
- **libnl**: Linux netlink 接口
- **zlib**: GZIP 压缩支持
- **lz4**: LZ4 压缩支持
- **zstd**: ZSTD 压缩支持
- **Asciidoctor**: 文档生成（可选）

## 编译指导

### CMake 配置选项
```bash
# 最小化构建（仅 TShark，无 GUI）
cmake -DBUILD_wireshark=OFF \
      -DBUILD_tshark=ON \
      -DCMAKE_BUILD_TYPE=Release \
      /path/to/wireshark-source

# 完整构建（包括 GUI）
cmake -DBUILD_wireshark=ON \
      -DBUILD_tshark=ON \
      -DCMAKE_BUILD_TYPE=Release \
      /path/to/wireshark-source
```

### 常见问题
1. **GLib 未找到**: 需要先编译并安装 GLib 2.x (>= 2.50.0)
2. **Qt 版本不兼容**: 需要 Qt >= 5.9，推荐使用最新 LTS 版本
3. **libpcap 缺失**: 需要安装 libpcap 开发包

## 已知限制
- GUI 版本（Wireshark）依赖 Qt，在嵌入式或服务器环境可能不需要
- 数据包捕获功能需要 root 权限或特殊设备权限
- 部分协议解析器依赖额外的库（如 libgcrypt）

## 功能验证
```bash
# 验证 TShark 版本
tshark --version

# 验证捕获能力
tshark -D  # 列出可用捕获接口

# 验证文件解析
tshark -r test.pcap
```

## 补丁清单
<!-- patches/ 目录中的补丁说明 -->

## 相关版本
- 4.4.16 (2026-05-25): 编译失败，缺少 GLib 依赖