# libtirpc

TI-RPC（Transport Independent RPC）库，提供现代的RPC（Remote Procedure Call）实现，支持TCP和UDP传输协议。

## 功能特性

- 提供完整的RPC API实现
- 支持TCP和UDP传输协议
- 提供XDR（External Data Representation）编码/解码功能
- 支持IPv4和IPv6
- 可选的GSS-API安全支持（本版本已禁用）

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [1.3.3](./1.3.3/) | built | 2026-05-22 |

## 平台适配说明

### OpenHarmony平台限制

编译过程中遇到以下OpenHarmony平台限制：

1. **HMDFS文件系统权限限制**
   - HMDFS不允许在当前目录创建临时子目录
   - 解决方案：将源码复制到 `/data/storage/el2/base/tmp-build/` 编译

2. **aclocal perl依赖问题**
   - aclocal-1.16脚本shebang指向错误perl路径
   - 解决方案：创建perl符号链接

3. **GSS-API可选依赖**
   - 使用 `--disable-gssapi` 禁用GSS-API功能
   - 对OpenHarmony平台不影响核心功能

## 使用方法

通过cmd-pkgs公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libtirpc 1.3.3
```

安装后文件位置：
- 库文件：`~/usr/local/lib/libtirpc.so*`
- 头文件：`~/usr/local/include/tirpc/`
- 配置文件：`~/usr/local/etc/netconfig`

## 编译选项

- `--prefix=/storage/Users/currentUser/usr/local` - 安装路径
- `--disable-gssapi` - 禁用GSS-API安全功能（可选依赖）

## 参考资料

- 官方源码：https://sourceforge.net/projects/libtirpc/
- 相关文档：TI-RPC编程指南