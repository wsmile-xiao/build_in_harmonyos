# hexedit 1.6 适配笔记

## 编译环境
- 构建系统：autotools
- 编译日期：2026-05-27
- 编译器：clang 15.0.4（OHOS SDK）
- 状态：published

## 编译步骤

1. 从 cmd-pkgs 预编译包安装 ncurses 6.4 依赖（libncursesw.a + 头文件）
2. 修改 configure：`cross_compiling=no`→`maybe`，`umask 077`→`022`（HMDFS 平台适配）
3. 执行 configure：
   ```bash
   ./configure --prefix=$DEFAULT_PREFIX HELP2MAN=/bin/true \
     CFLAGS="-fPIC -O2 -I$DEFAULT_PREFIX/include" \
     LDFLAGS="-L$DEFAULT_PREFIX/lib" \
     LIBS="-lncursesw"
   ```
4. `make -j1` → 生成 hexedit 二进制（3个format警告，0错误）
5. `make install DESTDIR=$TEST_PREFIX` → staging 安装
6. `make check` → hexedit 无 check 目标（跳过）
7. `ohc-run.py package` → hexedit-1.6-ohos-aarch64.tar.gz（329KB）
8. `make install` → 本地安装到 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 "cannot run C compiled programs" | HMDFS 安全机制阻止 conftest 执行 | sed `cross_compiling=no`→`maybe` |
| 2 | configure 创建临时目录失败 | umask 077 在 HMDFS 上不兼容 | sed `umask 077`→`022` |
| 3 | ncurses 编译辅助工具(make_hash)无法执行 | HarmonyOS 禁止执行未签名二进制 | 改用 cmd-pkgs 预编译包安装 ncurses |

## 源码修改

- configure：`cross_compiling=no`→`maybe`（3处），`umask 077`→`022`（2处）
- hexedit 源码无 config.guess/config.sub，configure 内联处理平台检测

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| ncurses | 6.4 | 宽字符版本 libncursesw.a，通过 cmd-pkgs 预编译包安装（R4：--without-shared） |

## 功能验证结果

### 命令行参数验证
- `hexedit --help`：✅ 显示用法信息
- `hexedit -s/-m/--color/-l<n>`：✅ 参数解析正确

### 交互模式验证
设置 `TERMINFO=$DEFAULT_PREFIX/share/terminfo` 和 `TERM=linux` 后：
- 十六进制显示：✅ 正确显示文件十六进制内容
- ASCII显示：✅ 正确显示文件 ASCII 内容
- 二进制数据：✅ 正确处理 00/FF 等非打印字符
- 文件名显示：✅ 界面标题显示文件名
- 地址偏移：✅ 00000000 格式正确

### ncurses 链接验证（R4铁律）
- 动态依赖：✅ 仅 libc.so（ncurses 静态链接，无 .so）
- 函数引用：✅ initscr 等 ncurses 函数已静态合并

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| hexedit-1.6-ohos-aarch64.tar.gz | 329KB | 预编译包（含ELF签名，可执行） |
| hexedit-1.6-ohos-aarch64-debug.tar.gz | 77KB | 调试符号包 |

## 注意事项

- hexedit 无 config.guess/config.sub 文件，平台适配通过修改 configure 实现
- hexedit 无 make check 目标
- 交互模式需设置 `TERMINFO` 和 `TERM` 环境变量（HarmonyOS 默认 terminfo 不完整）
- 打包签名版二进制可在 HarmonyOS 上正常执行
---

**编译结束**：2026-05-27 01:31
**最终状态**：published