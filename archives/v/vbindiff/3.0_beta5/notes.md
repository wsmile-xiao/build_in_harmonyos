# vbindiff 3.0_beta5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++ (OpenHarmony aarch64)
- 状态: published

## 编译步骤

1. 从 GitHub madsen/vbindiff 仓库 e478092 提交下载源码
2. 手动下载 GetOpt 子模块 (madsen/free-getopt) 并解压到工作目录
3. 运行 autoreconf -fvi 生成 configure 脚本
4. 手动生成 ncurses 头文件 (curses.h 从 curses.h.in 模板替换变量)
5. 添加缺失的 KEY_* 常量定义到 curses.h (KEY_DOWN=0402 等)
6. 添加 extern "C" 闭合括号和 C++ #undef box/clear/erase/move/refresh
7. 修复 unctrl.h 中的 @NCURSES_SP_FUNCS@ 未替换变量
8. 在 ConWin.hpp 中添加 #undef clear 和 #undef move 防止 ncurses 宏冲突
9. 运行 configure --prefix=$DEFAULT_PREFIX
10. 创建 man page (vbindiff.1) 替代缺失的 Perl Template 生成版本
11. 运行 make -j1 编译成功
12. 运行 make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Savannah 下载源不可达 | 网络问题 | 使用 GitHub 源码 (madsen/vbindiff e478092) |
| 2 | GetOpt 子模块缺失 | git submodule 未初始化 | 手动从 GitHub 下载 madsen/free-getopt |
| 3 | ncurses 头文件缺失 | 预编译包不含开发头文件 | 从 ncurses 6.4 源码 curses.h.in 手动生成 |
| 4 | KEY_* 常量未定义 | curses.h.in 模板不含全部 KEY_ 定义 | 手动添加 KEY_DOWN=0402 至 KEY_MAX=0777 |
| 5 | extern "C" 未闭合 | curses.tail 内容缺失 | 添加闭合括号和 C++ #undef 代码 |
| 6 | C++ 函数重载冲突 | extern "C" 闭合导致重载失效 | 修复 extern "C" 闭合问题 |
| 7 | unctrl.h 有 @变量@ 未替换 | 手动复制时遗漏 | 替换 @NCURSES_SP_FUNCS@ 为 0 |
| 8 | man page 生成失败 | Perl Template 模块缺失 | 创建简单的 vbindiff.1 man page |

## 源码修改

- curses/ConWin.hpp: 添加 #undef clear 和 #undef move
- 创建简单 vbindiff.1 man page

## 依赖版本

- ncurses 6.4 (预编译包 + 手动生成头文件)

## 验证结果

```bash
$ ./vbindiff --version
VBinDiff 3.0_beta5
Copyright 1995-2017 Christopher J. Madsen
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| vbindiff | 317952 | ELF64 PIE aarch64 可执行文件 |

## 注意事项

- ncurses 头文件需要手动维护（curses.h 中 KEY_* 定义需确保完整）
- vbindiff 3.0_beta5 是开发版本，非正式发布版
- 需要 ncurses 预编译包作为依赖
---
**编译结束**: 2026-06-02 23:12  
**测试补充**: 2026-06-03 14:26  
**测试补充**: 2026-06-03 14:26  
**最终状态**: published

---

## 对话记录

### 第1轮 — 编译阶段
- 从 GitHub 下载 vbindiff e478092 源码
- 手动填充 GetOpt 子模块
- 从 ncurses 6.4 源码手动生成 curses.h（替换 @VAR@ 变量 + 补充 KEY_* 常量 + 添加 extern "C" 闭合）
- 在 ConWin.hpp 中添加 #undef clear/move
- 修复 unctrl.h 中 @NCURSES_SP_FUNCS@ 未替换
- 创建简易 vbindiff.1 man page
- 编译成功，二进制 --version 输出正确

### 第2轮 — 补充归档阶段
- 执行真实功能测试（--version/--help/ELF格式/动态依赖/健壮性）
- 创建 test-report.md（20 PASS, 1 WARN, 2 SKIP, 0 FAIL）
- 创建 README.md 软件说明文件
- 更新 manifest.yaml：补充 dependencies(ncurses/6.4)、configure_options、knowledge_gained(7条)、补丁分类标注
- 重新运行 ohc-run.py finish published

---

## 对话记录

### 第1轮 — 编译阶段
- 从 GitHub 下载 vbindiff e478092 源码
- 手动填充 GetOpt 子模块
- 从 ncurses 6.4 源码手动生成 curses.h（替换 @VAR@ 变量 + 补充 KEY_* 常量 + 添加 extern "C" 闭合）
- 在 ConWin.hpp 中添加 #undef clear/move
- 修复 unctrl.h 中 @NCURSES_SP_FUNCS@ 未替换
- 创建简易 vbindiff.1 man page
- 编译成功，二进制 --version 输出正确

### 第2轮 — 补充归档阶段
- 执行真实功能测试（--version/--help/ELF格式/动态依赖/健壮性）
- 创建 test-report.md（20 PASS, 1 WARN, 2 SKIP, 0 FAIL）
- 创建 README.md 软件说明文件
- 更新 manifest.yaml：补充 dependencies(ncurses/6.4)、configure_options、knowledge_gained(7条)、补丁分类标注
- 重新运行 ohc-run.py finish published
---

**编译结束**: 2026-06-03 14:34
**最终状态**: published
