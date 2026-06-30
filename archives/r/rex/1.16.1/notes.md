# rex 1.16.1 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-06-17
- 编译器: Perl 解释器 v5.42.2 (-harmonyos-thread-multi)
- 状态: published

## 编译步骤

Rex 是一个 Perl 模块/工具（来自 CPAN），使用 ExtUtils::MakeMaker 构建系统。

1. `perl Makefile.PL PREFIX=$DEFAULT_PREFIX` — 生成 Makefile
2. `make -j2` — 构建（纯 Perl 模块，无 C 编译）
3. `make install DESTDIR=$TEST_PREFIX` — DESTDIR 模式安装到 staging
4. 修复 bin/rex 和 bin/rexify 的 shebang（fixin 在此平台未正确替换）
5. `chmod +x bin/rex bin/rexify` — 修复执行权限
6. 通过 `cpan -T` 安装 13 个运行时 Perl 模块依赖
7. `make install` — 直接安装到 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | perl Makefile.PL 交互式提示 | Makefile.PL 在安装可选功能时弹出交互式 y/N 提示 | 回答 N 跳过（可选功能非必需）或使用 PERL_MM_USE_DEFAULT=1 |
| 2 | bin/rex shebang 空行 | ExtUtils::MakeMaker 的 fixin 在鸿蒙平台未正确替换 #!/usr/bin/env perl | 手动修复为 `#!/storage/Users/currentUser/usr/local/bin/perl` |
| 3 | make install 后缺少执行权限 | 安装的脚本权限为 -rw------- | `chmod +x bin/rex bin/rexify` |
| 4 | 运行时依赖缺失 | Rex 需要 Sort::Naturally、Hash::Merge、JSON::MaybeXS 等 13 个 CPAN 模块 | `cpan -T` 批量安装 |
| 5 | make test 失败 (11/85 文件) | 详见测试报告 | 三类失败：缺少测试模块(6)、PATH 差异(3)、文件系统限制(2) |

## 源码修改

无需源码修改。shebang 修复和执行权限修复在安装后处理（非源码补丁）。

## 依赖版本

- Perl: v5.42.2 (-harmonyos-thread-multi)
- ExtUtils::MakeMaker: 7.1101+
- make: GNU Make 4.4.1

### 通过 cpan 安装的运行时依赖

| 模块 | 版本 | 用途 |
|------|------|------|
| Sort::Naturally | 1.03 | 文件排序 |
| Digest::SHA | 6.04 | 哈希计算 |
| Hash::Merge | 0.302 | 哈希合并 |
| JSON::MaybeXS | 1.004008 | JSON 处理 |
| Text::Glob | 0.11 | 通配符匹配 |
| YAML | 1.31 | YAML 解析 |
| String::Escape | 2010.002 | 字符串转义 |
| Sub::Override | 0.12 | 子例程覆盖 |
| Digest::HMAC | 1.05 | HMAC 计算 |
| Net::OpenSSH | 0.84 | SSH 连接 |
| Devel::Caller | 2.06 | 调用者信息 |
| Data::Validate::IP | 0.31 | IP 地址验证 |
| XML::Simple | 2.25 | XML 解析 |

## 验证结果

```bash
# 版本验证
$ /storage/Users/currentUser/usr/local/bin/rex -v
(R)?ex 1.16.1

# make test 统计
Files=85, Tests=1263, 174 wallclock secs
Failed 11/85 test programs. 9/1263 subtests failed.
（详细分析见 reports/test-report.md）
```

## 注意事项

1. Rex 是纯 Perl 模块，无 C 编译部分，编译非常简单
2. 需要通过 cpan 安装 13 个运行时依赖模块，约需 10 分钟
3. shebang 修复和执行权限修复是平台特有问题，需在每次安装后处理
4. make test 失败不影响安装和使用：失败的测试均为环境/依赖问题而非核心代码缺陷
5. 缺少多个可选 Perl 模块依赖（AWS::Signature4, Test::Output, Test::UseAllModules 等），这些在运行时按需加载

---

**编译结束**: 2026-06-17 23:18
**测试执行**: 2026-06-18 11:40 (make test, 174s)
**最终状态**: published
