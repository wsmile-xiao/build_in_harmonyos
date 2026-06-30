# perl-perlio-via-timeout

PerlIO layer that adds read & write timeout to a handle.

- **模块名**: PerlIO::via::Timeout
- **版本**: 0.32
- **作者**: Damien "dams" Krotkine
- **许可**: Perl 5 (same terms as Perl itself)
- **CPAN**: https://metacpan.org/pod/PerlIO::via::Timeout

## 描述

PerlIO::via::Timeout 是一个 PerlIO 层，为文件句柄添加读写超时功能。
它基于 `setsockopt(SO_RCVTIMEO/SO_SNDTIMEO)` 实现，允许在读写操作
超过指定时间后自动返回错误。

## 构建系统

- ExtUtils::MakeMaker (Makefile.PL)
- 纯 Perl 模块，无需 C 编译器
- 无二进制产物

## 鸿蒙平台适配

### 编译

```bash
# 下载源码
curl -o PerlIO-via-Timeout-0.32.tar.gz \
  https://cpan.metacpan.org/authors/id/D/DA/DAMS/PerlIO-via-Timeout-0.32.tar.gz

# 构建
tar xf PerlIO-via-Timeout-0.32.tar.gz
cd PerlIO-via-Timeout-0.32
perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site
make
make install
```

### 使用方法

```perl
use PerlIO::via::Timeout;

# 文件句柄添加超时层
open my $fh, '<:via(Timeout)', 'file.txt';

# 设置超时（必须使用函数调用语法，不可用 -> 方法调用）
PerlIO::via::Timeout::read_timeout($fh, 2);   # 读超时 2 秒
PerlIO::via::Timeout::write_timeout($fh, 2);  # 写超时 2 秒
PerlIO::via::Timeout::enable_timeout($fh);     # 启用超时

# 读写操作
while (my $line = <$fh>) {
    print $line;
}
close($fh);
```

⚠️ **重要**: 该模块的 API 函数必须使用**函数调用语法** (`PerlIO::via::Timeout::function($fh, ...)`)，
不可使用类方法调用语法 (`PerlIO::via::Timeout->function($fh, ...)`)。
使用方法调用语法会导致 "failed to get file descriptor for filehandle" 错误。

### 验证结果

| 检查项 | 结果 |
|--------|------|
| 编译 | ✅ 通过 |
| G0 干净构建验证 | ✅ 通过 |
| G1-G4 质量门禁 | ✅ 全部通过 |
| 鸿蒙平台功能测试 | ✅ 15/15 通过 (100%) |
| finish 收尾 (6 步) | ✅ 全部通过 (finish_success) |
| 知识完整性检查 | ✅ 通过 (.knowledge-done) |
| HMDFS 兼容性 | ✅ 通过 |
| Socket 超时 | ✅ 通过 |
| PerlIO 层堆叠 | ✅ 通过 |
| 上库评估 | ✅ 符合要求 |

## 依赖

### 运行时
- Exporter >= 5.57
- PerlIO::via (core)
- Time::HiRes (core)

### 测试时
- Test::TCP (未安装，导致 t/01_socket_timeout.t 失败。功能测试已手动覆盖该场景)

## 文件清单

| 文件 | 说明 |
|------|------|
| packaging/perl-perlio-via-timeout-0.32-ohos-aarch64.tar.gz | 预编译包 (17943 bytes) |
| tests/functional_test.pl | 鸿蒙平台功能测试脚本 |
| reports/test-report.md | 测试报告 |
| reports/quality-report.md | 质量门禁报告 |
