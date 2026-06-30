# perl-json (JSON 4.10)

JSON 模块 - Perl 的 JSON 编解码实现

## 软件描述

JSON 4.10 是一个纯 Perl 实现的 JSON 编解码模块，用于在 Perl 程序中处理 JSON 数据格式。

### 特性

- **纯 Perl 实现**: 无需 XS 编译，无平台依赖
- **完整功能**: 支持编码、解码、格式化、错误处理
- **Unicode 支持**: 正确处理中文、Emoji 等字符
- **多种输出格式**: pretty、canonical、indent 等格式化选项
- **错误检测**: 无效 JSON、循环引用等错误检测
- **高兼容性**: Perl 5.10+ 完全兼容

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|----------|
| 4.10 | published | 2026-06-13 |

## 编译状态

**编译日期**: 2026-06-12
**编译器**: clang 18.1.8
**构建系统**: perl (Makefile.PL)
**状态**: published（已验证可用）

### 编译环境

- OpenHarmony (aarch64-unknown-linux-ohos)
- Perl 5.42.0
- clang 18.1.8

### 编译特点

- ✅ 纯 Perl 模块，无需 XS 编译
- ✅ 无 SELinux HMDFS 限制
- ✅ 用户可直接安装
- ✅ 测试套件完整（68个测试文件，26111个测试用例）

## 功能测试

**测试日期**: 2026-06-13
**测试结果**: ✅ 全部通过 (32/32)

### 测试覆盖

- 基本编码解码: ✅ 4/4
- 数据类型支持: ✅ 8/8
- Unicode 支持: ✅ 3/3
- 复杂数据结构: ✅ 3/3
- 特殊功能: ✅ 4/4
- 错误处理: ✅ 2/2
- 性能测试: ✅ 2/2
- 兼容性测试: ✅ 3/3
- 实际应用场景: ✅ 3/3

### 质量门禁

- G0 干净构建: ✅ PASS
- G1 二进制完整性: ✅ PASS
- G2 功能可用性: ✅ PASS
- G3 可移植性: ✅ PASS
- G4 档案完整性: ✅ PASS

## 安装指南

### 用户安装

```bash
# 使用 cmd-pkgs 公共安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- perl-json 4.10
```

### 验证安装

```bash
perl -MJSON -e 'print "JSON version: $JSON::VERSION\n"'
# 输出: JSON version: 4.10
```

### 使用示例

```perl
use JSON;

# 创建 JSON 对象
my $json = JSON->new;

# 编码 Perl 数据为 JSON
my $data = {name => "OpenHarmony", version => "4.10"};
my $json_string = $json->encode($data);
# 输出: {"name":"OpenHarmony","version":"4.10"}

# 解码 JSON 为 Perl 数据
my $decoded = $json->decode($json_string);
print $decoded->{name};  # 输出: OpenHarmony

# 格式化输出
my $pretty = JSON->new->pretty->encode($data);
# 输出格式化的 JSON（带换行和缩进）
```

## 性能特性

### 编码性能

- 测试: 1000 元素复杂数据，编码 100 次
- 耗时: 0.76 秒
- 评估: ✅ 快（纯 Perl 实现的良好性能）

### 解码性能

- 测试: 1000 元素 JSON，解码 100 次
- 耗时: 3.19 秒
- 评估: ✅ 可接受（纯 Perl 比 XS 慢，但性能充足）

## 依赖关系

### 编译依赖

- perl/5.42.0

### 运行依赖

- Perl 5.10+ (无其他依赖)

## 与其他 Perl 模块的对比

### vs perl-dbd-pg

| 特性 | perl-json | perl-dbd-pg |
|------|-----------|-------------|
| 模块类型 | 纯 Perl | Perl XS |
| 编译复杂度 | ✅ 简单 | ⚠️ 需特殊参数 |
| SELinux 限制 | ✅ 无限制 | ❌ XS 受限 |
| 安装方式 | ✅ 用户安装 | ⚠️ 需管理员 |
| 测试环境 | ✅ 无依赖 | ⚠️ 需 PostgreSQL |

### 优势

1. **简单编译**: 无需 XS 编译参数，无需 CPATH/LIBRARY_PATH
2. **无平台限制**: 纯 Perl 实现，可在任何 Perl 环境运行
3. **用户友好**: 用户可直接安装，无需管理员权限
4. **高测试覆盖**: 68 个测试文件，26111 个测试用例

## 平台兼容性

- ✅ OpenHarmony (aarch64-unknown-linux-ohos)
- ✅ Linux (x86_64, aarch64)
- ✅ macOS
- ✅ Windows (Strawberry Perl)

## 文档资源

- [编译笔记](./4.10/notes.md) - 详细编译步骤和问题解决方案
- [测试报告](./4.10/reports/test-report.md) - 功能测试详细结果
- [质量报告](./4.10/reports/quality-report.md) - 质量门禁检查结果

## 上库信息

**状态**: published
**发布日期**: 2026-06-13
**发布渠道**: cmd-pkgs

**上库理由**:
1. 所有质量门禁通过（G0-G4）
2. 功能测试全部通过（32/32）
3. 文档完整（manifest、notes、test-report）
4. 用户可直接安装使用
5. 无 SELinux 限制

## 注意事项

1. **纯 Perl 性能**: 解码速度比 XS 版本慢，但对大多数应用场景足够
2. **无 SELinux 问题**: 因为是纯 Perl 模块，无 .so 文件限制
3. **无需管理员**: 用户可直接安装到 ~/usr/local
4. **完整测试**: make test 会执行 68 个测试文件，26111 个测试用例

## 更新历史

- 2026-06-12: 编译完成，状态 built
- 2026-06-13: 功能测试完成，质量门禁通过，状态升级为 published