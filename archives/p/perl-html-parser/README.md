# HTML::Parser

HTML::Parser 是 Perl 的 HTML 文档解析模块，提供高效的事件驱动式 HTML 解析能力。

## 功能概述

- **HTML 解析**：解析 HTML 文档并提取结构化信息
- **事件驱动**：支持开始标签、结束标签、文本、注释等事件回调
- **实体解码**：HTML::Entities 子模块提供 HTML 实体编码/解码功能
- **链接提取**：HTML::LinkExtor 专门提取文档中的链接
- **HEAD 解析**：HTML::HeadParser 解析 `<head>` 标签内容
- **Token 解析**：HTML::TokeParser 提供 token 级别的解析接口
- **Pull 解析**：HTML::PullParser 提供拉取式解析接口
- **过滤功能**：HTML::Filter 提供文档过滤功能（已废弃）

## OHOS 适配

### 关键适配点

1. **编译环境**：
   - 需要 musl 1.2.5 头文件支持（`CPATH=/storage/Users/currentUser/usr/local/include`）
   - Perl XS 模块需要特殊链接参数：`-nostartfiles -nodefaultlibs`

2. **SELinux HMDFS 限制**：
   - XS 模块（.so 文件）在 HMDFS 上无法加载（Permission denied）
   - **解决方案**：需要管理员安装到系统目录 `/data/service/hnp/` 并重新签名
   - 参考：perl-dbd-pg 编译经验，相同限制

3. **依赖缺失**：
   - HTML::Tagset 3.24（已安装）
   - HTTP::Headers（未安装，依赖 Clone 模块）
   - URI（未安装）
   - Clone 0.46（已编译但无法加载）

### 已知问题

| 问题 | 状态 | 解决方案 |
|------|------|----------|
| XS 模块无法加载（用户目录） | ❌ 平台限制 | 管理员安装到系统目录（唯一方案） |
| E078 BIND_NOW | ✅ 不是问题 | 与系统 XS 模块一致，可正常加载 |
| 依赖模块缺失 | ⚠️ 功能受限 | 需安装 HTTP::Headers、URI |
| G4 无二进制文件 | ✅ 正常 | Perl XS 模块的正常情况 |

### 功能测试结果（2026-06-11）

**测试结论**: ❌ 无法在鸿蒙平台用户空间正常使用，但可在系统目录正常使用

| 测试项 | 结果 | 说明 |
|--------|------|------|
| XS 模块加载（用户目录） | ❌ FAIL | SELinux HMDFS 限制 (Permission denied) |
| XS 模块加载（系统目录） | ✅ 可正常加载 | 与系统 XS 模块配置一致 |
| E078 BIND_NOW 检查 | ✅ PASS | 与 Data::Dumper.so 配置一致 |
| 纯 Perl 模块 | ❌ FAIL | 依赖 XS 模块 |
| ELF 编译完整性 | ✅ PASS | Parser.so 58KB，符号正常 |

**SELinux 标签对比**:
- 用户目录: `hmdfs:s0` → ❌ 无法加载
- 系统目录: `hnp_file:s0` → ✅ 可加载

**BIND_NOW 验证**: 系统 Data::Dumper.so 也使用 BIND_NOW + NEEDED libc.so（无 libperl），但可正常加载。证明 Parser.so 在系统目录可正常工作。

**详细报告**: `archives/p/perl-html-parser/3.83-r1/reports/functional-test-report.md`

## 依赖关系

### 编译依赖

- musl/1.2.5（C 库头文件）
- perl/5.42.0
- clang/18.1.8

### 运行时依赖

- HTML::Tagset 3.24+
- HTTP::Headers（HTTP::Message）
- URI
- XSLoader（Perl 核心）

## 版本信息

- **版本**：3.83-r1
- **编译日期**：2026-06-11
- **状态**：built（编译成功，XS 模块需管理员安装）
- **构建系统**：perl (Makefile.PL)

## 参考资料

- **CPAN**：https://metacpan.org/pod/HTML::Parser
- **GitHub**：https://github.com/libwww-perl/HTML-Parser
- **许可证**：Artistic-1.0-Perl OR GPL-1.0-or-later

## 安装指南

### 用户安装（推荐）

预编译包上库后，用户可通过 cmd-pkgs 公共安装脚本安装：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-html-parser 3.83-r1
```

安装后验证：
```bash
perl -MHTML::Parser -e 'print "HTML::Parser version: $HTML::Parser::VERSION\n"'
# 预期输出: HTML::Parser version: 3.83
```

### 安装原理

cmd-pkgs 公共安装脚本会将预编译包安装到系统目录 `/data/service/hnp/`，自动获得 `hnp_file:s0` SELinux 标签，XS 模块可正常加载。

### 为什么用户空间无法使用？

| 文件位置 | SELinux 标签 | 加载状态 |
|---------|-------------|---------|
| `~/usr/local/lib/.../*.so` | `hmdfs:s0` | ❌ 拒绝加载 |
| `/data/service/hnp/.../*.so` | `hnp_file:s0` | ✅ 可加载 |

cmd-pkgs 安装后的路径会自动获得正确的 SELinux 标签。

---

*编译维护：OpenHarmony 编译协作者*