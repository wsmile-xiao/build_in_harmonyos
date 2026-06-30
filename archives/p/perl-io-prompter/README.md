# IO::Prompter — OpenHarmony 编译记录

## 简介

IO::Prompter 是一个 Perl 模块，提供高级终端输入提示功能。支持多种输入类型验证、默认值、历史记录、自动完成等特性。

## 基本信息

| 项目 | 值 |
|------|-----|
| 名称 | IO::Prompter |
| CPAN 名称 | IO-Prompter |
| 版本 | 0.005004 |
| 构建系统 | Perl (ExtUtils::MakeMaker) |
| 许可证 | Artistic-1.0-Perl OR GPL-1.0-or-later |
| 官网 | https://metacpan.org/pod/IO::Prompter |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| 系统版本 | HarmonyOS HongMeng Kernel 1.12.0 |
| 架构 | aarch64 |
| Perl 版本 | 5.42.0 |
| 编译器 | clang |

## 编译步骤

```bash
# 1. 下载源码
wget https://cpan.metacpan.org/authors/id/D/DC/DCONWAY/IO-Prompter-0.005004.tar.gz
tar -xzf IO-Prompter-0.005004.tar.gz
cd IO-Prompter-0.005004

# 2. 配置
perl Makefile.PL PREFIX=$HOME/usr/local

# 3. 编译
make

# 4. 安装（DESTDIR 模式）
make pure_install DESTDIR=$HOME/tmp/test-install-perl-io-prompter-0.005004-r0

# 5. 验证
perl -I$HOME/usr/local/lib/site_perl/5.42.0 -e 'use IO::Prompter; print "OK\n";'
```

## OHOS 适配要点

1. **构建系统**：使用 Perl 的 ExtUtils::MakeMaker，不支持标准 configure/make 流程
2. **DESTDIR 模式**：使用 `make pure_install` 而非 `make install`，DESTDIR 参数仍然有效
3. **ELF 签名**：纯 Perl 模块无需签名（无二进制文件）
4. **依赖处理**：编译时警告运行时依赖，但不阻塞安装

## 运行时依赖

| 依赖模块 | 版本要求 | 说明 |
|---------|---------|------|
| Contextual::Return | - | 上下文返回值处理 |
| match::smart | 0.010+ | 智能匹配功能 |

编译时会警告缺少依赖，但不阻塞安装。运行前需安装依赖模块。

## 已知问题与平台限制 ⚠️

### 1. XS 模块加载限制（核心阻塞问题）⚠️ 2026-06-12 更新

**调查结果**:
- XS 模块可以成功编译（使用 `-nostartfiles` 标志）
- 但 XS 模块无法从用户目录加载
- 鸿蒙安全策略限制：只有系统目录 `/data/service/hnp/...` 允许加载 `.so` 文件

**验证证据**:
```bash
# 系统 XS 模块 ✅
dl_load_file("/data/service/hnp/.../Util.so") → 成功

# 用户 XS 模块 ❌
dl_load_file("~/perl5/.../Want.so") → Permission denied
```

**影响**: IO::Prompter 依赖 Want (XS)，无法在用户环境运行

### 2. XS 编译修复（2026-06-12 发现）

标准编译失败原因：缺少 crt 文件
```
ld.lld: error: cannot open crti.o: No such file or directory
```

**修复方法**: 使用 `-nostartfiles` 标志
```bash
clang -shared -nostartfiles -O2 -fstack-protector-strong \
      -L$HOME/usr/local/lib -Wl,-rpath,$HOME/usr/local/lib \
      source.o -o module.so
```

### 3. 运行时依赖情况

| 模块 | 类型 | 编译 | 加载 |
|------|------|------|------|
| Want | XS | ✅ 成功 | ❌ 阻塞 |
| Contextual::Return | 纯 Perl | ✅ 成功 | ✅ 可用 |
| match::smart | 纯 Perl | ✅ 成功 | ✅ 可用 |

由于 Want 无法加载，IO::Prompter 无法使用。

---

## 上库状态判断 ❌

**不建议上库发布到 cmd-pkgs**：

| 判断项 | 结果 | 说明 |
|--------|------|------|
| 编译成功 | ✅ | 模块文件完整 |
| XS 编译 | ✅ | Want.so 成功编译 |
| XS 加载 | ❌ | 平台安全策略阻塞 |
| 功能可用 | ❌ | 无法使用 |

**解决方案**:
1. 需要管理员将 XS 模块安装到系统目录
2. 使用纯 Perl 替代模块：IO::Prompt::Tiny, IO::Prompt::Simple

## 测试结果

详见 [test-report.md](./0.005004-r0/reports/test-report.md)

## 验证安装

```bash
# 检查安装文件
ls -la $HOME/usr/local/lib/site_perl/5.42.0/IO/Prompter.pm

# 加载测试
perl -I$HOME/usr/local/lib/site_perl/5.42.0 -e 'use IO::Prompter; print "OK\n";'
# 预期输出：警告缺少依赖，但模块本身可加载

# 功能测试（需安装依赖后）
perl -I$HOME/usr/local/lib/site_perl/5.42.0 -e 'use IO::Prompter; my $input = prompt "Test: "; print "Got: $input\n";'
```

## 经验总结

1. Perl 模块编译流程与 C/C++ 项目不同，使用 `perl Makefile.PL` 而非 `./configure`
2. 纯 Perl 模块（无 XS 代码）无需编译，直接安装即可
3. 模块依赖在编译时仅警告，运行时才真正需要
4. 质量门禁 G0-G3 通过，G4 因"无二进制文件"特殊性而豁免

## 参考资料

- CPAN: https://metacpan.org/pod/IO::Prompter
- 源码: https://cpan.metacpan.org/authors/id/D/DC/DCONWAY/IO-Prompter-0.005004.tar.gz