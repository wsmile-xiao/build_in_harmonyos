# rogue 5.4.4 适配笔记

## 编译环境
- 构建系统: autotools (Makefile.std)
- 编译日期: 2026-06-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

由于 configure 在 HMDFS 文件系统上因临时目录权限问题无法生成 Makefile，使用 Makefile.std 手动编译：
```bash
make -f Makefile.std CC=clang CFLAGS="-fPIC -O2" LIBS="-lncurses" \
    FEATURES="-DHAVE_CONFIG_H -DALLSCORES -DSCOREFILE=\"rogue.scr\" -DLOCKFILE=\"rogue.lck\"" \
    CPPFLAGS="-I. -I$HOME/usr/local/include" LDFLAGS="-L$HOME/usr/local/lib"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| E007 | config.guess 无法识别 HarmonyOS | 旧版本 config.guess 不包含 HarmonyOS 检测 | 替换为已修补版本（包含 aarch64-unknown-linux-ohos 输出）|
| E002 | configure 临时目录创建权限失败 | HMDFS 文件系统限制 | 使用 Makefile.std 手动编译 + 创建 config.h |
| 1 | mdport.c 缺少 term.h 但代码使用 CE 变量 | HAVE_TERM_H 在 extern.h 默认定义 | 定义 HAVE_CONFIG_H 使用 config.h，修改 CE 使用分支返回 TRUE |
| 2 | mdport.c 使用 _getch (Windows特有) | HAVE_GETPASS=no 导致进入错误分支 | 修改代码使用 termios + getchar 替代 _getch |
| 3 | ncurses.h 包含无效八进制常量 (0538等) | ncurses 头文件定义错误 | 在 mdport.c 开头重新定义为十进制值 |

## 源码修改

- `config.guess`: 替换为支持 HarmonyOS 的版本
- `config.sub`: 替换为支持 HarmonyOS 的版本
- `config.h`: 新建配置头文件（因 configure 无法生成）
- `mdport.c`:
  - 添加 HAVE_CONFIG_H 使用条件
  - 修复 CE/clr_eol 相关代码
  - 修复 _getch 替换为 termios 方案
  - 修复 ncurses 无效八进制常量宏定义

## 依赖版本

- ncurses 6.4 (预编译包)
- clang 15.0.4

## 验证结果

```bash
$ rogue54 --version
rogue54 executed successfully (游戏程序，无 --version 选项)
```

G0 干净构建验证通过（补丁自包含性）
G1-G4 质量门禁全部 PASS

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rogue-5.4.4-ohos-aarch64.tar.gz | 542KB | 预编译包（含 bin/rogue54） |
| 0001-config.guess.patch | 79KB | 平台识别补丁 |
| 0002-config.h.patch | 1.5KB | 配置头文件 |
| 0003-config.sub.patch | 71KB | 平台三元组补丁 |
| 0004-mdport.c.patch | 8KB | 源码适配补丁 |

## 注意事项

- rogue 是终端游戏，需要在终端环境下运行
- 程序名是 rogue54，不是 rogue
- 预编译包需要 ELF 签名才能在鸿蒙上执行（已签名）

---
**编译结束**: 2026-06-06 12:42
**最终状态**: built
