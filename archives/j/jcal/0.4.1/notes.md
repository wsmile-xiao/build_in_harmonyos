# jcal 0.4.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-26
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 源码包不含 configure 脚本，需先运行 libtoolize + autoreconf 生成
2. configure.in 修改: 添加 AC_CONFIG_AUX_DIR([.]) 和 AC_CONFIG_MACRO_DIR([m4]) 前置
3. ./configure --prefix=$DEFAULT_PREFIX --disable-shared --enable-static
4. make -j1 && make install DESTDIR=$TEST_PREFIX
5. make check (无测试目标)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoreconf 失败: install.sh anachronism | libtoolize 将辅助文件放在 ../.. 目录，automake 发现旧式 install.sh | 在 configure.in 中添加 AC_CONFIG_AUX_DIR([.]) |
| 2 | config.status: Permission denied (mktemp) | HMDFS setgid + umask 077 创建 mode 2700 目录，chmod 不生效 (E046) | 创建 mktemp wrapper 覆盖 umask 为 022 |
| 3 | 源码包无顶层目录 | tarball 直接包含源文件，无 jcal-0.4.1/ 包装目录 | conanfile.py source() 使用 strip_root=False |
| 4 | conanfile.py replace_in_file 找不到 configure.in | build() 在 build folder 运行，非 source folder | 使用 os.path.join(self.source_folder, "configure.in") |
| 5 | test_package CMake target 名错误 | Conan CMakeDeps 生成 jcal::jcal 而非 jcal::jalali | CMakeLists.txt 使用 jcal::jcal |

## 源码修改

- configure.in: 添加 AC_CONFIG_AUX_DIR([.])，AC_CONFIG_MACRO_DIR([m4]) 前置，版本号更新为 0.4.1
- conanfile.py build() 中使用 replace_in_file 自动修复 configure.in

## 依赖版本

无外部依赖

## 验证结果

conan-verify: 全部 8 道门禁通过 (G0-G4, L2/L4/L5)

## 注意事项

- jcal 是终端工具（日历显示），R26 静态链接: --disable-shared --enable-static + LDFLAGS=-static
- 源码包不含 configure 脚本，conanfile.py 需调用 autoreconf
- HMDFS 环境 mktemp 需 wrapper 修复 umask 问题
---

**编译结束**: 2026-06-29 16:00
**最终状态**: published
