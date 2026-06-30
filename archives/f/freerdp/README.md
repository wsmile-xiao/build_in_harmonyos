# FreeRDP

FreeRDP 是一个免费的远程桌面协议 (RDP) 实现库，用于连接 Windows 远程桌面服务。

## 基本信息

- **官网**: https://www.freerdp.com/
- **源码**: https://github.com/FreeRDP/FreeRDP
- **许可证**: Apache-2.0
- **类型**: 共享库 + 命令行工具

## 编译版本

| 版本 | 状态 | 编译日期 | 依赖 |
|------|------|----------|------|
| 3.26.0 | built | 2026-05-26 | zlib/1.3.1, openssl/3.5.6 |

## 特性

- Windows Portable Runtime (WinPR) 库
- FreeRDP 核心协议实现
- 客户端库（无图形客户端）
- 开发工具（winpr-hash, winpr-makecert）

## 使用方法

### 链接库

```cmake
find_package(FreeRDP 3 REQUIRED)
find_package(WinPR 3 REQUIRED)

target_link_libraries(your_target PRIVATE freerdp3 winpr3)
```

### 命令行工具

```bash
# 设置库路径
export LD_LIBRARY_PATH=/storage/Users/currentUser/usr/local/lib:$LD_LIBRARY_PATH

# 使用 WinPR 工具
winpr-makecert  # 生成证书
winpr-hash      # 计算哈希
```

## 注意事项

1. **客户端受限**: 当前版本禁用了 X11/Wayland/SDL，无图形客户端（xfreerdp）
2. **仅提供库文件**: 编译产物主要是库文件和开发工具，适合作为依赖库使用
3. **RPATH 问题**: 可执行文件需要正确设置库路径才能运行
4. **依赖路径**: CMake 配置需要手动指定依赖路径

## 编译选项

主要禁用的可选依赖：
- FFmpeg（视频编码）
- Cairo（图形渲染）
- Wayland/X11（图形客户端）
- Kerberos（认证）
- ICU（国际化，使用 builtin unicode 替代）
- CUPS（打印）
- channels（插件通道）
- server（服务器功能）