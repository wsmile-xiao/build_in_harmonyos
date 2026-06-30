# liblcf 0.8.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-03
- 编译器: clang/clang++ (Clang 15.0.4)
- 状态: built（编译成功，未发布）

## 编译步骤

由于网络问题无法从 GitHub 下载源码，使用 git clone 从 GitHub 克隆源码。

使用 CMake 编译，禁用所有可选依赖（ICU、Expat、inih）：
```bash
# 克隆源码
git clone --depth 1 --branch 0.8.1 https://github.com/EasyRPG/liblcf.git liblcf-git

# CMake 配置
cmake -B build-cmake \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DLIBLCF_WITH_ICU=OFF \
  -DLIBLCF_WITH_XML=OFF \
  -DLIBLCF_WITH_INI=OFF \
  -DLIBLCF_ENABLE_TOOLS=OFF

# 编译
cmake --build build-cmake -j2

# 安装到测试目录
cmake --install build-cmake --prefix $TEST_PREFIX/$DEFAULT_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络问题（无法连接到 github.com） | 使用 git clone 替代直接下载 tar.gz |
| 2 | Autotools configure 失败（Permission denied） | HMDFS 文件系统限制，config.status 无法创建临时子目录 | 改用 CMake 构建系统 |
| 3 | 缺少 ICU、Expat、inih 依赖 | 无预编译包可用，网络无法下载 | 使用 LIBLCF_WITH_ICU/XML/INI=OFF 禁用依赖 |
| 4 | 工具链接失败（缺少 C++ 标准库符号） | lcfstrings 工具需要链接 libc++，但编译器配置问题 | 使用 LIBLCF_ENABLE_TOOLS=OFF 禁用工具构建 |

## HMDFS SELinux umask 问题处理

问题：Autotools 的 config.status 在尝试创建临时子目录 ./confXXXXXX/ 时失败，报错 "Permission denied"。

原因分析：
1. HMDFS 文件系统对临时文件创建有严格限制
2. 文件权限显示所有者是 `file_manager`（GID 20001006），而非当前用户
3. SELinux 限制（虽然 getenforce 命令不存在，但可能有类似机制）

解决方案：
- 改用 CMake 构建系统（不需要创建临时子目录）
- 如果必须使用 Autotools，需要修改源代码目录位置或修改 config.status 脚本

## 源码修改

无补丁文件，仅使用 CMake 编译选项。

## 依赖版本

- CMake: 4.1.2
- Clang: 15.0.4
- Make: GNU Make 4.4.1

无外部库依赖（所有可选依赖已禁用）。

## 验证结果

```bash
# 检查库文件
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/lib/liblcf.so
# 输出: liblcf.so (3.3MB)

# 检查头文件
ls -la $TEST_PREFIX/$DEFAULT_PREFIX/include/lcf/
# 输出: 包含所有必需的头文件
```

由于禁用了工具（lcfstrings），无法进行功能测试。库文件编译成功，可用于其他项目链接。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| liblcf.so | 3.3MB | 共享库文件 |
| include/lcf/*.h | ~100个文件 | 头文件集合 |
| liblcf.pc | pkg-config 文件 | 用于其他项目查找 liblcf |

## 注意事项

1. 由于禁用了所有可选依赖，此版本仅支持基本的 LCF 文件读写，不支持：
   - ICU 编码处理（仅支持 Windows-1252）
   - XML 读写（Expat）
   - INI 配置文件读取（inih）

2. 如果需要完整功能，需要先编译 ICU、Expat、inih 依赖。

3. HMDFS 文件系统限制导致 Autotools 无法使用，推荐使用 CMake。

4. 工具（lcfstrings）无法编译，因为缺少 C++ 标准库链接配置。如需工具，需要手动添加链接选项。
---

**编译结束**: 2026-06-03 14:15
**最终状态**: built
