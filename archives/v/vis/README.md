# vis 0.9 for HarmonyOS aarch64

## 软件简介

vis 是一个高效的文本编辑器，基于 Plan 9 的结构化正则表达式。它结合了 vi(m) 的模态编辑和 sam 的命令语言，提供强大而简洁的文本处理能力。

### 主要特性
- **模态编辑**: 类似 vi/vim 的操作模式
- **结构化正则表达式**: sam 命令语言支持
- **多光标编辑**: 同时编辑多个位置
- **高效文本管理**: 优化的内部数据结构
- **终端支持**: curses 或 vt100 后端
- **Lua 扩展**: 可选的脚本支持

## 编译信息

- **版本**: 0.9
- **编译日期**: 2026-06-09
- **编译器**: clang 15.0.4
- **目标平台**: HarmonyOS aarch64
- **链接方式**: 静态链接

## 构建配置

### Configure 参数
```
--enable-curses=no   # 使用 vt100 终端后端
--enable-lua=no      # 禁用 Lua 脚本支持
--enable-tre=no      # 禁用 TRE 正则库
```

### 编译环境
- CC: clang
- CFLAGS: -fPIC -O2
- LDFLAGS: -static

## 补丁说明

本次编译未使用任何补丁文件。

所有兼容性问题通过以下方式解决：
1. 手动编译依赖库
2. 禁用不适用的特性
3. 手动修复配置文件

## 依赖说明

### 必需依赖（手动编译）

#### libtermkey (0.22)
- **用途**: 终端键盘输入处理
- **编译方式**: 静态库
- **来源**: https://github.com/neovim/libtermkey

#### unibilium (2.1.2)
- **用途**: terminfo 数据库解析
- **编译方式**: 静态库
- **来源**: https://github.com/neovim/unibilium

### 可选依赖（未启用）

#### ncurses / curses
- **用途**: 完整终端界面支持
- **状态**: 未编译（使用 vt100 后端替代）

#### Lua 5.2+
- **用途**: 脚本扩展支持
- **状态**: 未启用

#### libtre
- **用途**: 更高效的正则表达式
- **状态**: 未启用

## 安装文件

### 可执行文件
- `bin/vis` - 主程序 (575KB)
- `bin/vis-clipboard` - 剪贴板支持 (2.3KB)
- `bin/vis-complete` - 自动补全 (1.5KB)
- `bin/vis-digraph` - 特殊字符输入 (194KB)
- `bin/vis-menu` - 菜单界面 (112KB)
- `bin/vis-open` - 文件打开对话框 (1.9KB)

### 文档文件
- `share/doc/vis/LICENSE` - 许可证
- `share/doc/vis/README.md` - 项目说明
- `share/man/man1/*.1` - 手册页面

## 使用说明

### 运行 vis
```bash
# 直接运行
vis [文件名]

# 查看帮助
:help
```

### 基本操作
- `i` - 进入插入模式
- `Esc` - 返回普通模式
- `:w` - 保存文件
- `:q` - 退出
- `:wq` - 保存并退出

### 注意事项
1. 本版本使用 vt100 终端后端，功能受限
2. 无颜色主题支持
3. 无 Lua 脚本扩展
4. 终端能力检测依赖预设的 TERMINFO 路径

## 遇到的问题

### 问题 1: 必需依赖缺失
**描述**: libtermkey 和 unibilium 在系统中未安装
**影响**: configure 失败
**解决**: 手动编译这两个库的静态版本

### 问题 2: 版本号宏未替换
**描述**: termkey.h.in 中版本号变量未被正确处理
**影响**: 编译失败
**解决**: 手动修复头文件中的版本号宏定义

### 问题 3: TERMINFO 未定义
**描述**: unibilium 需要 terminfo 数据库路径
**影响**: 编译失败
**解决**: 编译时定义 TERMINFO 和 TERMINFO_DIRS 宏

### 问题 4: libtool 不可用
**描述**: 鸿蒙系统缺少 libtool 工具
**影响**: 无法按标准方式构建共享库
**解决**: 使用 llvm-ar 手动创建静态库

## 功能限制

由于编译配置限制，本版本有以下功能缺失：

1. **无颜色支持**: curses 未启用，无法使用主题
2. **无脚本扩展**: Lua 未启用，无法使用扩展脚本
3. **受限的终端能力**: vt100 后端功能较少
4. **无高级正则**: TRE 未启用，使用标准正则

## 改进建议

### 短期改进
1. 编译 ncurses 以启用完整终端支持
2. 配置 terminfo 数据库路径

### 长期改进
1. 编译 Lua 启用脚本扩展
2. 编译 libtre 提升正则性能
3. 添加 HarmonyOS 特定补丁优化

## 许可证

ISC License (类似 BSD)

## 参考资料

- 官方网站: https://martanne.github.io/vis/
- GitHub: https://github.com/martanne/vis
- 手册: vis(1), vis-lua(1)
- Wiki: https://github.com/martanne/vis/wiki