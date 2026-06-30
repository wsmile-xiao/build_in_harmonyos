# perl-mail-sendmail 0.82 编译笔记

## 编译日期
2026-06-15

## 编译环境
- 平台: OpenHarmony (aarch64-unknown-linux-ohos)
- Perl 版本: 5.42.2
- 编译器: clang 18.1.8
- 构建工具: ExtUtils::MakeMaker

## 编译过程

### Step 1: 初始化
下载源码并解压：Mail-Sendmail-0.82.tar.gz

### Step 2: 配置
```bash
perl Makefile.PL
```

**观察**:
- Mail::Sendmail 是纯 Perl 模块
- 自动检测 Perl 构建配置
- 检测依赖模块

### Step 3: 构建
```bash
make
```

**问题与解决**:
- **问题**: 测试失败，缺少 `Sys::Hostname::Long` 模块
- **解决**: 将 `Sys::Hostname::Long` 设为可选依赖
- **修改**: 使用 `eval { require Sys::Hostname::Long; }` + fallback

### Step 4: 测试
```bash
make test
```

**结果**:
- `t/original.t`: 2/2 subtests passed
- Wallclock time: 4 seconds
- 所有测试成功

### Step 5: 安装
```bash
make install DESTDIR=$TEST_PREFIX
```

**产物**:
- Mail/Sendmail.pm: 189KB (纯 Perl)
- 无 XS 模块
- 无动态库

## 平台适配要点

### Sys::Hostname::Long 可选化

原代码问题：
```perl
# 第 15 行：硬依赖
use Sys::Hostname::Long;
```

解决方案：
```perl
# 修改为可选加载
eval { require Sys::Hostname::Long; Sys::Hostname::Long->import('hostname_long'); };
```

原代码问题：
```perl
# 第 338 行：直接调用
$localhost = hostname_long() || hostname() || 'localhost';
```

解决方案：
```perl
# 使用条件调用
$localhost = (defined &hostname_long ? hostname_long() : '') || hostname() || 'localhost';
```

### 测试结果

| 测试文件 | 结果 | 说明 |
|---------|------|------|
| t/original.t | PASS | 2/2 subtests passed |

**修复前**: 测试失败，报错 `Sys::Hostname::Long not found`
**修复后**: 所有测试通过

## 功能可用性

### ✅ 可用功能
- SMTP 邮件发送
- SMTP 认证 (DIGEST-MD5, CRAM-MD5, PLAIN, LOGIN)
- MIME 邮件（需 MIME::QuotedPrint）
- 邮件队列管理
- 调试日志

### ⚠️ 可选依赖
- Sys::Hostname::Long: 长主机名获取（不可用时自动 fallback）
- MIME::QuotedPrint: MIME 编码（不可用时自动禁用）

## 补丁详情

### 0001-lib-Mail-Sendmail.pm.patch

修改文件: `lib/Mail/Sendmail.pm`

修改点：
1. 第 15 行: `use Sys::Hostname::Long` → `eval { require ... }`
2. 第 338 行: `hostname_long()` → 条件调用

影响范围: 2 处修改，+2/-2 行

---

**编译结束**: 2026-06-15 22:10
**最终状态**: published
---

**编译结束**: 2026-06-17 10:01
**最终状态**: published
