# fdupes 2.4.0 Conan 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 适配日期: 2026-08-27
- 编译器: clang/clang++
- 状态: conan adapted (full build, no feature trimming)

## 历史背景

历史归档 (2026-05-21) 使用手动编译方式，禁用了 ncurses 和 sqlite3。
本次 Conan 适配启用全部功能，不裁剪任何特性。

## 依赖 (Conan 管理)

| 依赖 | Conan 版本 | 用途 |
|------|-----------|------|
| ncurses | 6.4 | 交互式 curses 界面 (ncursesw wide character) |
| pcre2 | 10.45.1 | 32位正则表达式支持 (pcre2_match_32) |
| sqlite3 | 3.49.1 | 哈希数据库缓存 |

## 构建方式

使用 Conan AutotoolsToolchain 管理:
1. configure 自动查找 ncursesw (pkg-config fallback to AC_SEARCH_LIBS)
2. AC_SEARCH_LIBS 查找 pcre2-32 和 sqlite3
3. umask 077 → 022 修复 HMDFS 兼容性
4. OHOS 交叉编译: --build=x86_64-unknown-linux-gnu --host=aarch64-linux-ohos

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 无法创建临时文件 | HMDFS 不支持 ./confXXXXXX (E002) | umask 077→022 + conan build folder 在非 HMDFS 路径 |
| 2 | 历史构建禁用了 ncurses/sqlite | 设备缺少 pcre2-32 和 sqlite3 库 | 使用 conan 依赖管理，CI 环境自动拉取 |

## 源码修改

无源码修改，仅 configure 脚本的 umask 修复 (build() 方法内运行时替换)。

## 补丁

无补丁。历史 7 个补丁为 autotools 辅助文件的版本差异 (automake 1.16.1→1.18.1)，
在 CI 环境中 configure 可正常运行，无需补丁。
---

**编译结束**: 2026-08-27 11:30
**最终状态**: built
