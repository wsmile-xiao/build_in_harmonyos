# pg_top v4.1.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖：libbsd 0.11.7 (cmd-pkgs)、libmd 1.1.0 (cmd-pkgs)
2. 创建 m_harmonyos.c（基于 m_linux.c，因为 HarmonyOS 使用 /proc 文件系统）
3. 修改 CMakeLists.txt 添加 HarmonyOS 平台处理（使用静态 libncursesw.a 而非共享 stub）
4. 重命名 screen.c 中的 PC 全局变量为 pg_top_PC（避免与 libncursesw.a 中的 PC 冲突）
5. cmake 配置：cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release ..
6. make -j2 编译
7. make install DESTDIR=$TEST_PREFIX（staging 安装）
8. make install（直接安装到 $DEFAULT_PREFIX）
9. 验证：$DEFAULT_PREFIX/bin/pg_top --version → pg_top 4.1.3

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 找不到 m_harmonyos.c | uname -s 返回 HarmonyOS，无对应机器模块 | 创建 m_harmonyos.c（基于 m_linux.c） |
| 2 | 链接失败: unable to find library -lmd | libbsd 依赖 libmd，未安装 | 安装 libmd 1.1.0 预编译包 |
| 3 | 运行时找不到 libtinfow.so.6 / libbsd.so.0 | ncurses 用 --without-shared 编译(R4)，.so 是 stub；缺少版本化符号链接 | 修改 CMakeLists.txt 链接静态 libncursesw.a；创建 libbsd.so.0/libmd.so.0 版本化符号链接 |
| 4 | duplicate symbol: PC | screen.c 的 PC 与 libncursesw.a 的 PC 冲突 | 重命名 pg_top 的 PC 为 pg_top_PC |

## 源码修改

| 文件 | 原因 | 方式 | 补丁状态 |
|------|------|------|----------|
| machine/m_harmonyos.c | HarmonyOS 平台支持 | 基于 m_linux.c 创建 | 待 refresh-patch |
| CMakeLists.txt | 静态链接 ncurses (R4) | 添加 HarmonyOS 分支 | 待 refresh-patch |
| screen.c | PC 符号冲突 | 重命名 PC 为 pg_top_PC | 待 refresh-patch |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| PostgreSQL (libpq) | 9.4.13 | 预装 |
| ncurses | 6.4 | 预装（--without-shared 静态库） |
| libbsd | 0.11.7 | cmd-pkgs 预编译包 |
| libmd | 1.1.0 | cmd-pkgs 预编译包 |
| libintl | 8 | 预装 |

## 验证结果

```bash
$DEFAULT_PREFIX/bin/pg_top --version
pg_top 4.1.3
```

## 注意事项

- pg_top 使用 CMake 构建，不是 autotools
- ncurses 必须用静态库（--without-shared, R4 铁律）
- libbsd/libmd 需要版本化符号链接
- m_harmonyos.c 基于 m_linux.c，依赖 /proc 文件系统
---

**编译结束**: 2026-06-09 20:03
**最终状态**: built
