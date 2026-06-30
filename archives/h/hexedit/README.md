# hexedit

**hexedit** 是一个控制台十六进制文件编辑器，基于 ncurses 提供交互式终端界面。
允许用户以十六进制和 ASCII 两种模式查看与编辑文件内容。

## 功能特性

- 十六进制和 ASCII 双模式查看/编辑文件
- 支持搜索十六进制/ASCII 字符串
- 支持撤销/重做修改操作
- 支持在文件中标记书签位置
- 支持比较两个文件内容

## 已编译版本

- **1.6**（已发布，2026-05-27）
- 依赖：ncurses/6.4
- 构建系统：autotools
- 编译器：clang 15.0.4（OHOS SDK）

## 鸿蒙适配说明

### 补丁修改

1. **configure 脚本适配**：`cross_compiling=no` → `cross_compiling=maybe`
   （HarmonyOS 安全机制阻止 configure 生成的 conftest 测试程序执行）
2. **configure umask 适配**：`umask 077` → `umask 022`
   （HMDFS 文件系统在 umask 077 创建的目录下无法写入文件）

### ncurses 链接

- 使用 `libncursesw.a`（宽字符版本的静态库）进行静态链接
- 严格遵守 R4 铁律（`--without-shared`），不产生 .so 动态库
- 二进制中 ncurses 函数已静态合并，无动态 ncurses 依赖

### 终端配置要求

hexedit 交互模式需要正确的 terminfo 数据库。建议部署时设置环境变量：

```bash
export TERMINFO=$HOME/usr/local/share/terminfo
export TERM=linux   # 或 vt100
```

### 测试结果

- 命令行参数解析：✅ 全部通过
- 交互模式文件显示：✅ 通过（需配置 TERMINFO）
- 二进制结构：✅ ELF64 aarch64, 静态 ncurses
- 文档：✅ man page 完整