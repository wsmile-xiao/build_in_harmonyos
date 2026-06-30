# perl-mime-charset 1.013.1 适配笔记

## 编译环境
- 构建系统: perl (Makefile.PL)
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- Perl 版本: 5.42.0
- 状态: published

## 编译步骤

1. 源码从 CPAN/MetaCPAN 下载: `https://cpan.metacpan.org/authors/id/N/NE/NEZUMI/MIME-Charset-1.013.1.tar.gz`
   - 注意: 初始搜索找到的 Savannah URL 返回 404，实际在 CPAN (作者: NEZUMI)
   - Python urllib 有 SSL 证书验证问题，使用 curl 下载后通过 file:// URL 加载
2. `perl Makefile.PL` — 成功，可选依赖跳过
3. `make` — 成功，纯 Perl 模块拷贝
4. `make install DESTDIR=$TEST_PREFIX` — staging 安装成功
5. `make test` — 101 测试全部通过（8 个因可选依赖跳过）
6. Staging 验证通过
7. `ohc-run.py package` — 成功打包 (74KB)
8. `make install` — 安装到 $DEFAULT_PREFIX (~/usr/local)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载失败 (SSL) | Python urllib SSL 证书验证 | 使用 curl 下载到本地，通过 file:// URL 加载 |
| 2 | G0 clean-verify 失败 | 纯 Perl 模块无 ./configure，G0 尝试运行 ./configure 返回 127 | 平台限制，已手动验证通过 |
| 3 | G4 manifest 缺少 build_system | 模板使用 build.system 嵌套格式，G4 检查 build_system 顶层字段 | 添加 build_system: perl 顶层字段 |
| 4 | 缺少软件级文件 | 初次编译未创建软件级 manifest.yaml 和 README.md | 根据 perl-dbd-pg 经验补全软件级文件 |

## 从 perl-dbd-pg 编译经验借鉴的改进

借鉴 perl-dbd-pg 3.18.0 的编译经验，对 perl-mime-charset 进行以下改进：

1. **补全软件级文件**: 创建 archives/p/perl-mime-charset/manifest.yaml 和 README.md
2. **完善 manifest 字段**: 添加 dependencies、build_dependencies 等完整字段
3. **补充 reviewer-report.md**: 参照 perl-dbd-pg 的评估报告格式，生成完整的上库评估报告
4. **增强功能测试**: 从 perl-dbd-pg 的详细功能测试中学到，需要覆盖多语言、边界情况，从 101 项扩展到 138 项测试

## 依赖版本

- Perl: 5.42.0
- Test::More: 1.302210
- Encode: 3.21 (>= 1.98 满足要求)

## 验证结果

```bash
# 模块加载验证
$ perl -MMIME::Charset -e 'print $MIME::Charset::VERSION, "\n"'
1.013.1

# 功能验证
$ perl -MMIME::Charset -e 'use MIME::Charset; my $cs = MIME::Charset->new("UTF-8"); print $cs->as_string'
UTF-8

# 官方测试套件
$ make test
All tests successful.
Files=10, Tests=101,  3 wallclock secs
Result: PASS

# 自定义功能测试 (37项)
$ perl ~/tmp/test_mime_charset.pl
Total: 37 | Pass: 37 | Fail: 0
Pass Rate: 100.0%
Result: PASS ✅
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-mime-charset-1.013.1-ohos-aarch64.tar.gz | 74KB | 预编译包 |

## 预编译包内容

```
lib/site_perl/5.42.0/MIME/Charset.pm          — 主模块
lib/site_perl/5.42.0/MIME/Charset/_Compat.pm   — 兼容层
lib/site_perl/5.42.0/MIME/Charset/UTF.pm      — UTF处理
lib/site_perl/5.42.0/MIME/Charset/Defaults.pm.sample — 配置示例
lib/site_perl/5.42.0/POD2/JA/MIME/Charset.pod   — 日文文档
lib/site_perl/5.42.0/aarch64-linux/auto/MIME/Charset/.packlist — 安装清单
```

## 注意事项

- 纯 Perl 模块，无原生二进制，G0 clean-verify 因无 ./configure 而失败（平台限制）
- G1-G4 门禁全部通过（G2 有 1 个 ⚠️ 因无可测试二进制，正常）
- 可选依赖未安装（Encode::EUCJPASCII 等），对应测试跳过，不影响核心功能
- 相比 perl-dbd-pg 的 XS 模块，纯 Perl 模块不受 SELinux/HMDFS 限制，安装后立即可用
---

**编译结束**: 2026-06-18
**最终状态**: published
