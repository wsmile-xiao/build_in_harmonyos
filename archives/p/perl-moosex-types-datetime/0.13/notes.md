# perl-moosex-types-datetime 0.13 适配笔记

## 编译环境
- 构建系统: Perl (Makefile.PL / ExtUtils::MakeMaker)
- 编译日期: 2026-06-23 (初次) / 2026-06-24 (依赖修复 + 测试通过)
- 编译器: clang/clang++
- 状态: built (可升级为 published)

## 编译步骤

1. 下载源码包 `MooseX-Types-DateTime-0.13.tar.gz` 并解压
2. `perl Makefile.PL PREFIX=$DEFAULT_PREFIX` 生成 Makefile
3. `make` 编译模块（纯 Perl 模块，无 XS 编译）
4. `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
5. `make install` 安装到 `$DEFAULT_PREFIX`（~/usr/local）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make test 失败 (2/4 文件) | 运行时依赖未安装 | 安装 DateTime 1.66、DateTime::Locale 1.45、DateTime::TimeZone 2.68 |
| 2 | DateTime 1.66 XS 编译失败 | musl 头文件不完整（缺少 endian.h） | 利用 DateTime 的纯 Perl 回退机制，手动安装 .pm 文件 |
| 3 | DateTime::Duration 缺失 | DateTime 包未完全安装 | 随 DateTime 一起手动安装 |

### DateTime XS 编译失败详情

DateTime 1.66 的 XS 组件 (`DateTime.xs`) 编译时遇到 `sys/types.h` -> `endian.h` 依赖链断裂：

```
perl.h:1117:10: fatal error: 'sys/types.h' file not found
```

**根因**: musl 头文件备份目录 `_sysheaders_backup/` 不完整，缺少 `endian.h`。

**解决方案**: DateTime 模块内置纯 Perl 回退机制（`DateTime::PP`），XSLoader 失败时自动使用 PP 实现。手动安装 .pm 文件后，DateTime 正常工作于纯 Perl 模式，功能完整。

## 源码修改

无补丁。本模块为纯 Perl 模块，无需修改源码。

## 依赖版本

| 依赖 | 所需版本 | 实际版本 | 来源 |
|------|---------|---------|------|
| Perl | 5.008003 | 5.042000 | 系统预装 |
| Moose | 0.41 | 2.4000 | 系统预装 |
| MooseX::Types | 0.30 | 0.51 | 系统预装 |
| MooseX::Types::Moose | 0.30 | 0.51 | 系统预装 |
| DateTime | 0.4302 | 1.66 | CPAN (纯 Perl 模式) |
| DateTime::Duration | 0.4302 | 1.66 | CPAN (随 DateTime) |
| DateTime::Locale | 0.4001 | 1.45 | CPAN |
| DateTime::TimeZone | 0.95 | 2.68 | CPAN |
| namespace::clean | 0.19 | 0.27 | 系统预装 |
| Test::Fatal | 任意 | 0.017 | 系统预装 |
| Test::More | 0.88 | 1.302210 | 系统预装 |

## 验证结果

```bash
# make test 全部通过
cd ~/tmp/builds/perl-moosex-types-datetime-0.13.work
make test
# All tests successful.
# Files=4, Tests=27, 2 wallclock secs
# Result: PASS

# 模块加载验证
perl -MMooseX::Types::DateTime -e 'print MooseX::Types::DateTime->VERSION, "\n"'
# 0.13

# 功能验证
perl -e '
use Moose;
use DateTime;
use MooseX::Types::DateTime qw(DateTime Duration);
has "ts" => (is => "rw", isa => "DateTime", coerce => 1, default => sub { DateTime->now() });
my $obj = main->new();
print $obj->ts->iso8601, "\n";
'
# 2026-06-24T08:35:20
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-moosex-types-datetime-0.13-ohos-aarch64.tar.gz | 16.5KB | 预编译包 |

## 注意事项

1. **DateTime 纯 Perl 模式**: DateTime 1.66 运行于纯 Perl 模式（XS 因 musl 头文件不完整无法编译）。功能完整，性能略低于 XS 模式。
2. **DateTime 依赖链**: 若用户重新安装或升级 DateTime，需确保 DateTime::Locale 和 DateTime::TimeZone 同步安装。
3. **纯 Perl 模块**: 本模块（MooseX::Types::DateTime）本身是纯 Perl 模块，无 XS 组件，无编译风险。

---

**编译结束**: 2026-06-24 16:36
**最终状态**: built (测试全部通过，可上库)
