# vis 0.9 编译笔记

## 项目信息
- **软件名称**: vis - 高效文本编辑器
- **版本**: 0.9
- **来源**: https://github.com/martanne/vis
- **构建系统**: configure + make

## 编译环境
- **编译器**: clang 15.0.4
- **目标平台**: HarmonyOS aarch64
- **C 标准库**: musl libc
- **构建日期**: 2026-06-09

## 依赖处理

### 1. libtermkey (必需依赖)
- **来源**: https://github.com/neovim/libtermkey
- **编译方式**: 手动编译静态库
- **关键步骤**:
  - 生成 termkey.h 头文件（替换版本号宏）
  - 编译源文件: termkey.c, driver-csi.c, driver-ti.c
  - 创建静态库: libtermkey.a
  - 创建 pkg-config 文件

### 2. unibilium (libtermkey 依赖)
- **来源**: https://github.com/neovim/unibilium
- **编译方式**: 手动编译静态库
- **关键步骤**:
  - 手动定义 TERMINFO 和 TERMINFO_DIRS 宏
  - 编译源文件: unibilium.c, uninames.c, uniutil.c
  - 创建静态库: libunibilium.a

## Configure 参数

### 完整命令
```bash
./configure --prefix=$HOME/usr/local \
  --enable-curses=no \
  --enable-lua=no \
  --enable-tre=no
```

### 参数说明
- `--enable-curses=no`: 禁用 ncurses，使用 vt100 终端后端
- `--enable-lua=no`: 禁用 Lua 脚本支持
- `--enable-tre=no`: 禁用 TRE 正则表达式库

### 关键发现
- libtermkey 是必需依赖，无法禁用
- 鸿蒙系统没有 ncurses，使用 vt100 后端
- 使用静态链接 (`-static`) 确保可移植性

## 编译过程

### 环境变量
```bash
export CC="clang"
export CFLAGS="-fPIC -O2"
export LDFLAGS="-L$HOME/usr/local/lib -static"
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig
```

### 编译命令
```bash
make -j2
make install DESTDIR=$TEST_PREFIX
```

### 编译结果
- ✅ 编译成功
- ✅ 生成静态可执行文件: vis (575KB)
- ✅ 生成辅助工具: vis-clipboard, vis-complete, vis-digraph, vis-menu, vis-open

## 遇到的问题

### 问题 1: libtermkey 未安装
**原因**: libtermkey 是 vis 的必需依赖，但系统未安装
**解决方案**: 手动编译 libtermkey 静态库

### 问题 2: unibilium 未安装
**原因**: libtermkey 依赖 unibilium 或 ncurses
**解决方案**: 手动编译 unibilium 静态库（更轻量）

### 问题 3: 版本号宏未替换
**原因**: termkey.h.in 中的版本号变量未正确替换
**解决方案**: 手动修复 termkey.h 中的版本号宏

### 问题 4: TERMINFO 未定义
**原因**: unibilium 需要 TERMINFO 路径定义
**解决方案**: 在编译时定义 TERMINFO 和 TERMINFO_DIRS 宏

### 问题 5: libtool 不可用
**原因**: 鸿蒙系统没有 libtool
**解决方案**: 手动使用 llvm-ar 创建静态库

## 测试结果

### 功能测试
- ✅ 可执行文件生成成功
- ✅ 二进制格式: ELF executable, 64-bit LSB arm64, static
- ⚠️ 无法运行完整功能测试（需要终端环境）

### 文件验证
- ✅ vis 主程序
- ✅ vis-clipboard
- ✅ vis-complete
- ✅ vis-digraph
- ✅ vis-menu
- ✅ vis-open
- ✅ 文档文件 (LICENSE, README.md)
- ✅ man 页面

## 编译状态总结

**最终状态**: ✅ SUCCESS

### 成功要素
1. 正确处理依赖链: unibilium -> libtermkey -> vis
2. 手动编译静态库避免动态链接问题
3. 使用 vt100 后端避免 ncurses 依赖
4. 静态链接确保可移植性

### 限制说明
- 无 Lua 脚本支持
- 无 TRE 正则表达式支持
- 无 ncurses 界面（使用 vt100 后端）
- 无颜色主题支持（依赖 curses）

### 后续改进建议
1. 编译 ncurses 以启用完整终端支持
2. 编译 Lua 以启用脚本扩展
3. 创建 terminfo 数据库以完善终端能力检测