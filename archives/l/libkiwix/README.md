# libkiwix

**Common code base for all Kiwix ports**

libkiwix is the core library for Kiwix, an offline reader for Web content.
It provides the common functionality shared across all Kiwix ports (desktop, mobile, etc.).

- **Homepage**: https://kiwix.org
- **Repository**: https://github.com/kiwix/libkiwix
- **Build System**: Meson (C++17)

## 部署说明

预编译包已修复以下问题：
- ✅ 绝对路径依赖已转换为相对路径
- ✅ 扁平化部署（所有依赖库在同一目录）
- ✅ 包含完整的依赖库（libpugixml.so 等）
- ✅ 包含完整的头文件（zim/*.h）

### 安装方法

```bash
# 解压预编译包
tar xzf libkiwix-14.2.1-ohos-aarch64.tar.gz

# 复制到安装目录
cp lib/*.so* $HOME/usr/local/lib/
cp bin/* $HOME/usr/local/bin/
cp -r include/* $HOME/usr/local/include/
cp lib/pkgconfig/*.pc $HOME/usr/local/lib/pkgconfig/

# 设置环境变量
export LD_LIBRARY_PATH=$HOME/usr/local/lib:$LD_LIBRARY_PATH

# 验证安装
kiwix-compile-resources --help
pkg-config --modversion libkiwix
```

### 依赖列表

| 依赖 | 版本 | 说明 |
|------|------|------|
| libzim | 9.7.0 | ZIM 文件格式库（已打包） |
| libxapian | 1.4.28 | 搜索引擎库（已打包） |
| libmicrohttpd | 1.0.5 | HTTP 服务器库（已打包） |
| libpugixml | 1.15 | XML 解析库（已打包） |
| libcurl | 系统库 | HTTP 客户端库（系统提供） |
| ICU | 77.1 | 国际化库（系统提供） |

## 验证结果

| 测试项 | 结果 |
|--------|------|
| 动态库加载 (dlopen) | ✅ 成功 |
| 工具运行 | ✅ kiwix-compile-* 正常 |
| API 功能 | ✅ Library/Book API 正常 |
| pkg-config | ✅ 版本 14.2.1 |
| 跨机器可移植 | ✅ 无绝对路径依赖 |

---

*修复日期: 2026-06-08*
