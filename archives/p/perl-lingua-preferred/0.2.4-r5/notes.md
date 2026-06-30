# perl-lingua-preferred 0.2.4-r5 适配笔记

## 编译环境
- 构建系统: perl (Makefile.PL)
- 编译日期: 2026-06-12
- 编译器: 无（纯 Perl 模块）
- 状态: published
- 目标平台: aarch64-unknown-linux-ohos

## 编译步骤

### 1. 源码下载
```bash
源码位于: Lingua-Preferred-0.2.4.tar.gz
```

### 2. 初始化编译环境
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build perl-lingua-preferred 0.2.4-r5 \
  --url=file:///storage/Users/currentUser/tmp/downloads/Lingua-Preferred-0.2.4.tar.gz
```

### 3. 配置
```bash
cd ~/tmp/builds/perl-lingua-preferred-0.2.4-r5.work
perl Makefile.PL
```

### 4. 编译
```bash
make
```

编译成功，生成：
- blib/lib/Lingua/Preferred.pm（纯 Perl 模块）

### 5. 测试
```bash
make test
```

测试结果：76 个测试全部通过（test.pl）

### 6. 安装
```bash
make install DESTDIR=~/tmp/test-install-perl-lingua-preferred-0.2.4-r5
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| - | 无问题 | 纯 Perl 模块，无 XS 代码，编译过程顺利 | 无需特殊处理 |

**备注**：相比 perl-dbd-pg（XS 模块），纯 Perl 模块的编译过程非常简单：
- 不需要设置 CPATH（无 C 编译）
- 不需要特殊链接参数（无 .so 文件）
- 不受 HMDFS SELinux 限制影响
- 可直接加载和运行

## 源码修改

无补丁。编译过程顺利，未修改源码。

## 依赖版本

- Perl: 5.42.0
- 可选依赖: Log::TraceMessages（未安装，不影响核心功能）

## 验证结果

### 模块加载测试
```bash
perl -MLingua::Preferred -e 'print $Lingua::Preferred::VERSION'
```

结果：0.2.4（正常加载）

### 功能测试
```bash
perl -e 'use Lingua::Preferred qw(which_lang); \
  my $lang = which_lang(["en", "de"], ["fr", "de"]); \
  print "最佳语言: $lang\n";'
```

结果：最佳语言: de（正常）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| Preferred.pm | ~6KB | Lingua::Preferred 纯 Perl 模块 |
| perl-lingua-preferred-0.2.4-r5-ohos-aarch64.tar.gz | 19KB | 预编译包 |

## 注意事项

1. **纯 Perl 模块**：无 XS 代码，不受 HMDFS SELinux 限制，可直接在用户目录加载。
2. **无依赖限制**：Log::TraceMessages 是可选依赖，缺失不影响核心功能（模块自动处理）。
3. **质量门禁 G4**：无二进制文件是纯 Perl 模块的正常情况，不影响发布。
4. **与 XS 模块对比**：
   - perl-dbd-pg（XS 模块）：需要 CPATH、特殊链接参数、受 HMDFS 限制
   - perl-lingua-preferred（纯 Perl）：无需特殊处理，编译简单

---

**编译结束**: 2026-06-15 10:18
**最终状态**: published