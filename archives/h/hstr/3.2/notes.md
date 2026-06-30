# hstr 3.2 编译笔记

## 编译环境

- 编译器: clang 15.0.4
- 构建系统: autotools (configure.ac + Makefile.am)
- 目标平台: OpenHarmony aarch64
- 源码来源: Git 仓库 v3.2 标签

## 编译过程

### Phase 1: 环境初始化

- 源码获取: 克隆 Git 仓库 https://github.com/dvorka/hstr (v3.2 标签)
- 构建系统: autotools (需要运行 autoreconf -i 生成 configure 脚本)
- 依赖项: ncursesw (静态库), readline, m

### Phase 2: 编译配置

1. **运行 autoreconf -i**: 生成 configure 脚本和 Makefile.in
2. **configure 失败**: PKG_CHECK_MODULES 宏未定义，导致 bash completion 检查失败
3. **configure.ac 修改**: 注释掉 PKG_CHECK_MODULES 相关代码（bash completion 功能）
4. **重新 autoreconf**: 成功生成 configure

**configure 参数**: `--prefix=/storage/Users/currentUser/usr/local`

### Phase 3: 编译与安装

1. **第一次 make 失败**: ncursesw/curses.h 文件不存在
   - 问题: 预编译的 ncursesw 只有 curses.h，没有 ncursesw/curses.h 目录
   - 解决: 修改 src/include/hstr.h 和 src/include/hstr_curses.h，将 `#include <ncursesw/curses.h>` 改为 `#include <curses.h>`

2. **第二次 make 失败**: KEY_END, KEY_DC, KEY_RESIZE 等宏未定义
   - 问题: curses.h 中缺少扩展 KEY_ 宏定义
   - 解决: 在 src/include/hstr.h 中添加缺失的宏定义：
     ```c
     #ifndef KEY_END
     #define KEY_END 0555
     #endif
     #ifndef KEY_DC
     #define KEY_DC 0532
     #endif
     #ifndef KEY_RESIZE
     #define KEY_RESIZE 0633
     #endif
     #ifndef KEY_PPAGE
     #define KEY_PPAGE 0523
     #endif
     #ifndef KEY_NPAGE
     #define KEY_NPAGE 0522
     #endif
     #ifndef KEY_ENTER
     #define KEY_ENTER 0527
     #endif
     ```

3. **第三次 make 成功**: 编译完成（有大量 ncurses 函数声明警告，但不影响链接）

4. **make install 失败**: HMDFS 文件系统不支持硬链接
   - 问题: install-exec-hook 中使用 `ln` 创建硬链接失败
   - 解决: 修改 src/Makefile.am，将硬链接改为软链接：
     ```makefile
     install-exec-hook:
         rm -f $(DESTDIR)$(bindir)/hh$(EXEEXT) && ln -s hstr$(EXEEXT) $(DESTDIR)$(bindir)/hh$(EXEEXT)
     ```

5. **最终安装成功**: hstr 和 hh (软链接) 已安装到 staging 目录

## 问题与解决

### 问题 1: PKG_CHECK_MODULES 宏缺失

**原因**: aclocal.m4 中缺少 pkg-config 的宏定义

**解决**: 注释掉 configure.ac 中的 PKG_CHECK_MODULES 相关代码

**影响**: 禁用了 bash completion 功能（不影响核心功能）

### 问题 2: ncursesw/curses.h 路径问题

**原因**: 预编译的 ncursesw 没有创建 ncursesw 子目录

**解决**: 修改源代码中的 #include 路径

**影响**: 所有需要 curses.h 的源文件

### 问题 3: KEY_ 宏定义缺失

**原因**: ncursesw 的 curses.h 不包含扩展宏定义

**解决**: 手动添加缺失的宏定义到 hstr.h

**影响**: hstr.c 中的键盘处理代码

### 问题 4: HMDFS 不支持硬链接

**原因**: OpenHarmony 的 HMDFS 文件系统限制

**解决**: 使用软链接替代硬链接（遵循 R5 铁律）

**影响**: install-exec-hook

## 补丁说明

### 源文件修改清单

1. **configure.ac**: 注释 PKG_CHECK_MODULES 相关代码
2. **src/include/hstr.h**:
   - 修改 #include <ncursesw/curses.h> 为 #include <curses.h>
   - 添加 KEY_END, KEY_DC, KEY_RESIZE 等宏定义
3. **src/include/hstr_curses.h**: 修改 #include 路径
4. **src/Makefile.am**: 修改硬链接为软链接

### 生成文件修改

- aclocal.m4, configure, Makefile.in 等由 autoreconf 重新生成
- **不在补丁中包含生成文件**（遵循 R6 铁律）

## 知识提取

### 新发现的错误模式

1. **ncursesw 头文件路径不完整**: 预编译的 ncursesw 可能只提供 curses.h，不提供 ncursesw/curses.h
2. **KEY_ 宏定义不完整**: curses.h 可能不包含扩展的 KEY_ 宏（KEY_END, KEY_DC 等）
3. **HMDFS 硬链接限制**: 必须使用软链接替代硬链接

### 平台适配要点

- ncursesw/curses.h → curses.h（路径适配）
- KEY_ 宏手动补充
- 硬链接 → 软链接（HMDFS 适配）
- PKG_CHECK_MODULES 缺失时禁用相关功能

---

**编译开始**: 2026-05-22 18:10
**编译结束**: 2026-05-22 18:23
**最终状态**: 成功 (built)
---

**编译结束**: 2026-05-22 18:24
**最终状态**: built
