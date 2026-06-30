# GNU Go

GNU Go 是一个自由软件围棋程序，能够与其他围棋程序或人类玩家进行对弈。

## 软件信息

- **软件名称**：GNU Go（gnugo）
- **官方网站**：https://www.gnu.org/software/gnugo/
- **最新版本**：3.8（本归档版本）
- **许可证**：GPL-3.0-or-later

## 功能特性

- 围棋引擎：支持 9x9、13x13、19x19 棋盘
- 多种模式：ASCII、GMP、GTP（Go Text Protocol）
- 强度可调：默认等级 10，可通过 --level 参数调整
- SGF 支持：可读取和生成 SGF 格式的棋局文件
- 回归测试：包含 13+ 个测试套件验证功能

## 编译版本

当前归档版本：**3.8**

### 编译信息

- **编译日期**：2026-06-16
- **平台**：HarmonyOS-aarch64
- **编译器**：clang-15.0.4
- **构建系统**：autotools

### 补丁说明

编译需要以下补丁：

1. `0001-fix-duplicate-symbol-liberty-h.patch` - 修复重复符号问题（liberty.h）
2. `0002-fix-duplicate-symbol-unconditional-c.patch` - 修复重复符号问题（unconditional.c）

### 平台适配问题

1. **HMDFS 文件系统限制**：需要设置 TMPDIR 环境变量并修改 config.status 脚本
2. **重复符号错误**：需要修复全局变量定义问题（见补丁）

## 使用方法

### 安装预编译包

```bash
# 通过 cmd-pkgs 安装
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gnugo 3.8
```

### 命令示例

```bash
# 显示版本
gnugo --version

# ASCII 模式（交互式）
gnugo --mode ascii

# GTP 模式（用于 GTP 客户端）
gnugo --mode gtp --level 10

# 加载 SGF 文件
gnugo --mode ascii -l game.sgf

# 评分估算
gnugo --score estimate -l game.sgf
```

## 文件列表

- `bin/gnugo` - 主程序（约 7.5MB）
- `share/man/man6/gnugo.6` - 手册页
- `share/info/gnugo.info*` - Info 文档

## 依赖

- **运行时依赖**：无特殊依赖（动态链接 musl）
- **编译时依赖**：无特殊依赖

## 质量门禁

- G0（干净构建）：✅ PASS
- G1（二进制完整性）：✅ PASS
- G2（功能可用性）：✅ PASS（回归测试通过）
- G3（可移植性）：✅ PASS（动态链接，无需 RPATH）
- G4（档案完整性）：✅ PASS

## 已知问题

- **ncurses 未检测到**：缺少彩色终端输出支持，不影响核心功能
- **编译警告**：约 100+ 个旧式 C 函数声明警告，不影响功能

## 参考资料

- GNU Go 官方网站：https://www.gnu.org/software/gnugo/
- GNU Go 文档：info gnugo
- SGF 格式规范：https://www.red-bean.com/sgf/

---

*最后更新：2026-06-16*