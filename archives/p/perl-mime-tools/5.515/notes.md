# perl-mime-tools 5.515 适配笔记

## 编译环境
- 构建系统: perl (Module::Install via inc::Module::Install)
- 编译日期: 2026-06-17
- 编译器: 不需要（纯 Perl 模块）
- 状态: built

## 编译步骤

```bash
# 1. 下载并解压源码
cd ~/tmp/builds/perl-mime-tools-5.515.work

# 2. 生成 Makefile
perl Makefile.PL
# 输出: Writing Makefile for MIME::Tools

# 3. 编译
make
# 输出: Skip blib/lib/MIME/*.pm (unchanged) — 所有 .pm 文件已就绪

# 4. 测试
make test
# 输出: All tests successful. Files=40, Tests=438
# 结果: PASS

# 5. 安装
make install
# 安装到 ~/usr/local/lib/site_perl/5.42.0/MIME/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | MIME::Decoder::Base64.pm 缺失 | make install 未将 Decoder/Base64.pm 复制到安装目录 | 手动复制 `cp lib/MIME/Decoder/Base64.pm ~/usr/local/lib/site_perl/5.42.0/MIME/Decoder/` |
| 2 | MYMETA.json/yml 补丁 | 构建时自动生成的元数据文件版本号差异 | 非源码补丁，已从 patches_applied 中移除 |
| 3 | encode_mimeword 参数顺序 | MIME::Words 模块函数签名为 `($text, $encoding, $charset)` | 确认文档，无需修改模块 |

## 源码修改

无源码修改。此模块为纯 Perl 实现，所有功能测试通过。

## 依赖版本

| 依赖 | 版本 | 状态 |
|------|------|------|
| Perl | 5.42.0 | ✅ |
| Mail::Header | 1.01+ | ✅ |
| Mail::Internet | 1.0203+ | ✅ |
| Mail::Field | 1.05+ | ✅ |
| MIME::Base64 | 3.16 | ✅ |
| IO::File | 1.13+ | ✅ |
| File::Temp | 0.18+ | ✅ |
| Test::More | (core) | ✅ |
| Test::Deep | (installed) | ✅ |

## 验证结果

```bash
# 模块加载验证
$ perl -MMIME::Tools -e 'print $MIME::Tools::VERSION'
5.515

# make test 结果
All tests successful.
Files=40, Tests=438, 13 wallclock secs
Result: PASS

# 功能测试（15 项）
通过: 15 | 警告: 0 | 失败: 0
详见 reports/test-report.md
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/perl-mime-tools-5.515-ohos-aarch64.tar.gz | 332KB | 预编译包（含 20 个 .pm 文件） |

## 注意事项

1. **Base64.pm 缺失问题**：首次安装时 `make install` 不会复制 `MIME::Decoder::Base64.pm`，需手动复制。已确认是 Module::Install 的已知行为，非 OpenHarmony 特有问题。
2. **纯 Perl 模块**：无 XS 组件，不受 SELinux/HMDFS 限制影响（与 perl-dbd-pg 不同，perl-dbd-pg 需要 XS 模块安装到系统目录）。
3. **MYMETA 补丁**：原打包生成的 0001-MYMETA.json.patch 和 0002-MYMETA.yml.patch 是构建元数据差异，非功能补丁，保留在 patches/ 目录但不影响编译。

---

**编译结束**: 2026-06-18 14:41
**最终状态**: built
