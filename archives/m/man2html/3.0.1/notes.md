# man2html 3.0.1 适配笔记

## 编译环境
- 构建系统: custom (Perl install.me 安装脚本)
- 编译日期: 2026-07-13
- 编译器: N/A (纯 Perl 脚本，无需 C 编译)
- 状态: built (待鸿蒙设备验证后标记 published)

## 软件信息

- **名称**: man2html
- **版本**: 3.0.1
- **作者**: Earl Hood (ehood@medusa.acs.uci.edu)
- **许可证**: GPL-2.0-or-later
- **来源**: Homebrew formula (实际版本 3.0.1)
- **主页**: https://savannah.nongnu.org/projects/man2html/
- **源码 URL**: https://www.mhonarc.org/release/misc/man2html3.0.1.tar.gz
- **SHA256**: a3dd7fdd80785c14c2f5fa54a59bf93ca5f86f026612f68770a0507a3d4e5a29

## 源码结构

```
man2html3.0.1/
├── CHANGES          # 变更历史
├── COPYING          # GPL 许可证
├── MANIFEST         # 安装清单 (install.me 使用)
├── README           # 说明文档
├── install.me       # Perl 安装脚本
├── man2html         # 主程序 (Perl 脚本)
├── man.cgi          # CGI 版本 (需手动安装)
└── doc/
    ├── man2html.1   # man page
    ├── man2html.html
    ├── man2html.ps
    └── man2html.txt
```

## 构建系统分析

man2html 是**纯 Perl 脚本工具**，不是 C/C++ 编译型软件：

1. **没有 configure/Makefile/CMakeLists.txt**
2. **安装脚本 install.me** 是 Perl 程序，负责：
   - 将 man2html 脚本复制到指定目录
   - 重写 man2html 的 `#!` 行指向实际 perl 路径
   - 安装 man page 到 man 目录
3. **batch 模式参数**（与 Homebrew formula 一致）：
   - `-batch`: 非交互模式
   - `-binpath <dir>`: 可执行文件安装目录
   - `-manpath <dir>`: man page 安装目录

## 编译步骤

```bash
# 1. 解压源码
tar xzf man2html3.0.1.tar.gz && cd man2html3.0.1

# 2. 安装 (batch 模式, 与 Homebrew formula 一致)
perl install.me -batch \
  -binpath /path/to/bin \
  -manpath /path/to/man

# 3. 验证
echo '.TH TEST 1' | man2html
```

## 依赖处理

| 依赖 | 类型 | 处理方式 |
|------|------|----------|
| perl | 系统运行时依赖 | 不声明 Conan require，参考 perl-spiffy 归档处理方式 |

**说明**: perl 在鸿蒙设备上作为系统工具存在，man2html 的 install.me 和 man2html 脚本本身都需要 perl 运行时。参考 archives/p/perl-spiffy/0.46/conanfile.py 的处理方式，直接调用 `perl` 命令，不通过 Conan 依赖管理。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 版本号混淆 | Debian man2html 是 1.6g，Homebrew man2html 是 3.0.1，两者不同 | 确认赛题清单版本为 homebrew，对应 Homebrew 的 3.0.1 版本 |
| 2 | 构建系统识别 | man2html 不是 C/C++ 编译型软件，是 Perl 脚本工具 | 使用 custom 构建系统，build() 调用 perl install.me |
| 3 | perl 依赖声明 | perl 未发布到 Conan 制品仓 (状态 partial) | 作为系统运行时依赖处理，不声明 Conan require |

## 源码修改

无补丁。man2html 3.0.1 源码未做任何修改，install.me 的 batch 模式原生支持非交互安装。

## 验证结果

```bash
# 烟雾测试: 将 nroff man page 转换为 HTML
echo '.TH TEST 1 "2026-07-13" "test 1.0" "User Commands"
.SH NAME
test \- sample man page' | man2html

# 预期输出包含 <html>/<body>/<h1> 等 HTML 标签
```

**注意**: 完整的 conan create 验证需要在鸿蒙设备上执行（SKILL.md 说明编译环境为 OHOS/aarch64 原生构建）。

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方 (custom 构建系统) |
| conandata.yml | 源码 URL + SHA256 |
| test_package/ | L1 消费者测试 (test.sh 烟雾测试) |
| commands.json | R38 命令行工具声明 (软件级) |
| manifest.yaml | 软件级 + 版本级元数据 |

## 注意事项

1. **版本目录名**: 使用 `3.0.1` (与实际版本号一致，CI 脚本用 basename 取版本号)
2. **perl 路径**: conanfile.py 中用 `shutil.which("perl")` 动态检测 perl 路径执行 install.me
3. **后续验证**: 需到鸿蒙设备执行 `conan create` 和 `conan-verify` 完成完整验证
4. **R38**: man2html 是命令行工具，已在软件级目录创建 commands.json
