# perl-string-shellquote 1.04-r5 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 从 CPAN 下载 String-ShellQuote-1.04.tar.gz
2. 初始化编译环境：`ohc-run.py init-build perl-string-shellquote 1.04`
3. 运行 `perl Makefile.PL` 配置（生成 Makefile）
4. 运行 `make -j1` 编译（纯 Perl 模块，无需 C 编译）
5. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
6. 运行 `make test` 执行上游测试套件
7. 生成 Conan 配方：`ohc-run.py conan-init perl-string-shellquote 1.04-r5`
8. 验证 Conan 配方：`ohc-run.py conan-verify perl-string-shellquote 1.04-r5`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | test_package 测试输出 `hello worldn` 而非 `hello world\n` | Python 字符串与 shell 转义层级嵌套导致 `\n` 被解释为字面 `n` | 重写 test_package 使用临时 Perl 脚本文件避免 shell 转义问题 |
| 2 | 上游 test.t 测试 30-33 失败（shell-quote 子进程找不到模块） | `via_shell` 函数 fork 的 `blib/script/shell-quote` 子进程未继承 `-Iblib/lib` | 设置 `PERL5LIB=blib/lib` 环境变量后全部 33 个测试通过 |
| 3 | notes.md/manifest.yaml/MANIFEST.yml 为模板占位符 | ohc-run.py finish 自动生成的骨架未填充 | 根据 perl-dbd-pg 经验手动填写完整文档 |

## 与 perl-dbd-pg 编译经验对比

| 方面 | perl-dbd-pg (XS 模块) | perl-string-shellquote (纯 Perl) |
|------|----------------------|----------------------------------|
| C 编译 | 需要（Pg.so 共享库） | 不需要 |
| CRT 文件缺失 | 遇到，需 `-nostartfiles -nodefaultlibs -lc` | 不适用 |
| SELinux HMDFS 限制 | 动态库加载受限 | 不适用（纯 Perl 文件） |
| 外部依赖 | libpq, pg_config, perl-dbi | 无（仅依赖 Perl 本身） |
| 补丁 | 需要（Makefile.PL 修改） | 不需要 |
| 编译复杂度 | 高 | 低 |

## 源码修改

无补丁。纯 Perl 模块无需任何源码修改即可在鸿蒙平台编译运行。

## 依赖版本

### 已存在
- Perl 5.42.0 (系统预装于 /data/service/hnp/perl.org/perl_5.42.0/)

### 编译依赖
- 无额外依赖（纯 Perl 模块，仅需 Perl 本身）

## 验证结果

### 上游测试套件 (test.t)
```bash
$ cd /tmp/builds/perl-string-shellquote-1.04-r5.work
$ PERL5LIB=blib/lib perl test.t
1..33
ok 1 - ok 33  (全部通过)
```

### Conan 验证 (conan-verify)
```bash
$ ohc-run.py conan-verify perl-string-shellquote 1.04-r5
G0: PASS  G1: PASS  G2: PASS  G3: PASS  G4: PASS
L2: PASS  L4: PASS  L5: PASS
```

### 功能测试
- 模块加载: PASS
- shell_quote 基本功能: PASS (12 项)
- shell_quote_best_effort: PASS (5 项)
- shell_comment_quote: PASS (5 项)
- null 字节异常处理: PASS
- shell-quote CLI 工具: PASS
- 总计: 27/27 PASS (功能测试) + 33/33 PASS (上游测试) = 60/60 全部通过

## 产物

| 文件 | 说明 |
|------|------|
| data/service/hnp/.../site_perl/5.42.0/String/ShellQuote.pm | Perl 模块文件 |
| data/service/hnp/.../bin/shell-quote | 命令行工具 |
| data/service/hnp/.../auto/String/ShellQuote/.packlist | 安装清单 |

## 知识沉淀

### 平台发现
- 纯 Perl 模块（无 XS/C 代码）在鸿蒙平台可直接编译，无需处理 CRT 文件缺失、SELinux 限制等问题
- Perl ExtUtils::MakeMaker 构建系统在鸿蒙平台兼容性良好
- 上游 test.t 中 fork 子进程测试需要设置 PERL5LIB 环境变量

### 编译建议
- 纯 Perl 模块编译流程：`perl Makefile.PL && make && make install DESTDIR=...`
- 无需补丁、无需特殊链接参数
- test_package 测试应避免复杂的 shell 转义，使用临时脚本文件更可靠

---

**编译结束**: 2026-07-06 14:44
**最终状态**: published (编译成功，conan-verify + CI 模拟全部通过)
