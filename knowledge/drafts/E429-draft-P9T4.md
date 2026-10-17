# E429 — conan perl 包空前缀安装导致 @INC 指向 //lib/perl5，Perl 脚本找不到核心模块

## 错误特征

```
Can't locate strict.pm in @INC (you may need to install the strict module)
(@INC entries checked: //lib/perl5/site_perl/5.42.2/aarch64-linux-thread-multi
 //lib/perl5/site_perl/5.42.2 //lib/perl5/vendor_perl/5.42.2/... //lib/perl5/5.42.2)
BEGIN failed--compilation aborted
```

任何核心模块（strict / warnings 等）都会以同样形式失败。

## 触发条件

- 构建系统: make / autotools / cmake 均可触发（只要构建期调用 conan perl 执行脚本）
- 阶段: configuration（代码生成脚本；实测于 pgTAP 1.3.4 的 `compat/gencore` 与
  `sql/uninstall_pgtap.sql` 生成）

## 根因分析

conan 制品仓的 perl 包以**空前缀**打包：perl 内建 @INC 因此是 `//lib/perl5/...`，
指向不存在的绝对路径，核心模块全部找不到。
实测（pgtap 1.3.4，perl/5.42.2.3）：`bin/perl --version` 可正常执行，但未设 PERL5LIB 时
`perl -e 'use strict'` 失败。

## 解决方案

### 推荐方案

构建命令前置 `PERL5LIB=<perl 包>/lib/perl5`（包内真实模块树）：

```bash
PERL_PKG="$(conan cache path perl/5.42.2.3:<pkgid>)"
PERL5LIB="$PERL_PKG/lib/perl5" make PERL="$PERL_PKG/bin/perl" ...
```

配方内对应 `self.run('PERL5LIB="<pkg>/lib/perl5" make ...')`。

### 禁止做法

- ❌ 向 `//lib/perl5` 拷贝/软链（绝对路径不可写且污染共享系统）
- ❌ 只依赖系统 perl 而不声明依赖（CI clean 环境无系统 perl）

## 验证

```bash
PERL_PKG=$(conan cache path perl/5.42.2.3:<pkgid>)
"$PERL_PKG/bin/perl" -e 'use strict'                          # 失败：Can't locate strict.pm
PERL5LIB="$PERL_PKG/lib/perl5" "$PERL_PKG/bin/perl" -e 'use strict'   # 成功（rc=0）
```

## 关联条目

- 相关: E077（ELF 签名）无关；本条为 conan perl 包消费方式问题
