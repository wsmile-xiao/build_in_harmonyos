# libzippp

libzippp 是 libzip 的 C++ 封装库，提供面向对象的接口用于创建、读取和修改 ZIP 归档文件。

## 基本信息

| 项目 | 值 |
|------|-----|
| 项目地址 | https://github.com/ctabin/libzippp |
| 许可证 | BSD-2-Clause |
| 构建系统 | CMake |
| 语言 | C++11 |
| 依赖 | libzip ≥ 1.10.1, zlib ≥ 1.3.1 |

## 已编译版本

| 版本 | 状态 | 日期 | 产物 |
|------|------|------|------|
| 7.1 | ✅ published | 2026-06-25 | libzippp-7.1-ohos-aarch64.tar.gz (121KB) |

## 产物说明

libzippp 编译为**静态库**，包含以下内容：

- `lib/libzippp_static.a` — 静态库
- `include/libzippp/libzippp.h` — C++ 头文件（ZipArchive, ZipEntry 等类）
- `share/libzippp/*.cmake` — CMake 配置文件（支持 find_package）

## 安装方式

```bash
# 通过 cmd-pkgs 公共安装脚本安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libzippp 7.1
```

## CMake 使用示例

```cmake
find_package(libzippp REQUIRED)
target_link_libraries(myapp PRIVATE libzippp::libzippp)
```

## 主要类

- `libzippp::ZipArchive` — ZIP 文件操作主类
- `libzippp::ZipEntry` — ZIP 条目（文件/目录）
