# IO::String - Perl 内存字符串 IO 模块

**软件名称**: perl-io-string
**版本**: 1.08
**发布状态**: published
**发布日期**: 2026-06-12
**平台**: aarch64-unknown-linux-ohos

---

## 简介

IO::String 是一个纯 Perl 模块，提供 IO::File 和 IO::Handle 兼容的接口，用于在内存字符串上进行文件操作。它是 IO::Scalar 和 IO-stringy 模块的替代方案，适用于需要在内存中处理字符串数据的场景。

## 特性

- **纯 Perl 实现**: 无 C/XS 代码，无需编译器
- **标准 IO 接口**: 兼容 IO::File 和 IO::Handle
- **内存高效**: 字符串操作无磁盘 IO
- **UTF-8 支持**: 支持 Unicode 字符编码
- **段落模式**: 支持按段落读取
- **seek/tell**: 支持文件指针定位操作

---

## 安装

### 从 cmd-pkgs 安装（推荐）

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-io-string 1.08
```

### 手动安装

```bash
tar -xzf perl-io-string-1.08-ohos-aarch64.tar.gz
# 解压到指定路径，设置 PERL5LIB 环境变量
```

---

## 使用示例

### 基本读写

```perl
use IO::String;

# 从字符串创建
my $io = IO::String->new("Hello, OpenHarmony!");
my $content = <$io>;
print $content;  # 输出: Hello, OpenHarmony!
```

### 写入操作

```perl
my $io = IO::String->new();
print $io "Line 1\n";
print $io "Line 2\n";
$io->seek(0, 0);
my @lines = <$io>;
```

### seek/tell 操作

```perl
my $io = IO::String->new("1234567890");
seek($io, 5, 0);  # 定位到位置 5
my $pos = tell($io);  # 返回 5
my $rest = <$io>;  # 读取 "67890"
```

### 段落模式

```perl
my $io = IO::String->new("Para 1\n\nPara 2\n\nPara 3");
local $/ = "";  # 段落模式
my $para1 = <$io>;  # 读取第一段
my $para2 = <$io>;  # 读取第二段
```

---

## 依赖

- Perl 5.6.0+ (核心依赖)

---

## 版本历史

| 版本 | 状态 | 发布日期 | 说明 |
|------|------|---------|------|
| 1.08 | published | 2026-06-12 | 功能验证通过，发布到 cmd-pkgs |

---

## 质量报告

- **测试通过率**: 100% (64/64)
- **质量门禁**: G0-G4 全部通过
- **性能数据**: 写入 ~870K 行/秒，读取 ~89K 行/秒

详细报告:
- 功能测试报告: archives/p/perl-io-string/1.08/reports/functional-test-report.md
- 上库评估报告: archives/p/perl-io-string/1.08/reports/publish-evaluation-report.md

---

## 相关文档

- CPAN 文档: https://metacpan.org/pod/IO::String
- 编译笔记: archives/p/perl-io-string/1.08/notes.md
- 版本 manifest: archives/p/perl-io-string/1.08/manifest.yaml

---

## 许可证

Perl Artistic License 或 GPL v1+（Perl 标准许可证）

---

## 维护者

上游作者: Gisle Aas (GAAS)
鸿蒙适配: OpenDesk AI Agent