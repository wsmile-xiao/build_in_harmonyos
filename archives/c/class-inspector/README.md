# class-inspector

[Class::Inspector](https://metacpan.org/pod/Class::Inspector) — 友好地获取
**已加载类**的信息（Perl）。

## 简介

Perl 里查「某个类是否已加载、它从哪个文件来的、里面有哪些函数和方法」本可以用
符号表硬做，但写法相当底层。Class::Inspector 把常用查询封装成一组简单接口。

| 方法 | 用途 |
|------|------|
| `installed( $class )` | 类是否已安装且在 `@INC` 内可解析 |
| `loaded( $class )` | 类是否已加载（即使它没有自己的文件、寄居在别的文件里也能识别）|
| `filename( $class )` | 类的 `@INC` **相对**路径，如 `Class/Inspector.pm` |
| `resolved_filename( $class )` | 走 `@INC` 解析出的**真实**文件路径 |
| `loaded_filename( $class )` | 该类**实际加载自**的路径 |
| `functions( $class )` | 类内全部函数名 |
| `function_refs( $class )` | 类内全部函数的 `CODE` 引用 |
| `function_exists( $class, $f )` | 指定函数是否存在 |
| `methods( $class, $type, $vis )` | 方法列表（可按 public/private 过滤）|
| `subclasses( $class )` | 已加载的子类列表 |

另有函数式接口 `Class::Inspector::Functions`，把常用查询导出为函数
（`@EXPORT`：`installed`/`loaded`/`filename`/`functions`/`methods`/`subclasses`；
`@EXPORT_OK`：`resolved_filename`/`loaded_filename`/`function_refs`/`function_exists`）。

```perl
use Class::Inspector;

Class::Inspector->installed( 'Foo::Class' );
Class::Inspector->loaded( 'Foo::Class' );
Class::Inspector->resolved_filename( 'Foo::Class' );
Class::Inspector->functions( 'Foo::Class' );
Class::Inspector->methods( 'Foo::Class', 'full', 'public' );
```

> ⚠️ `subclasses()` 有**三态**返回值：命中子类 → 数组引用；无命中 → **空字符串**；
> 类名非法 → **`undef`**。断言时不要一律按数组引用处理。

> ⚠️ 类名合法性校验请用 `_class()`；把非法类名喂给 `installed()`/`filename()`
> 会触发上游对 `undef` 路径的取值警告。

## OHOS 适配

- **纯 Perl 模块**：无 XS、无 C/C++ 编译、无平台相关代码；运行时仅依赖
  `File::Spec >= 0.80` 与 `base`（perl 核心模块），OHOS 行为与上游一致。
- **构建系统沿用上游**：本发行版自带 `Makefile.PL`，由 `Dist::Zilla` 生成、
  直接 `use ExtUtils::MakeMaker`，且发行版内**不含 `inc/`**（既非 Module::Install，
  也非 Module::Build）——因此 `perl Makefile.PL` 开箱可用，**不需要**生成替代构建
  脚本。配方对「源码根目录缺 `Makefile.PL`」显式报错，避免上游换构建系统时静默出错。
- **零补丁**：未改动任何上游文件，`patches: {}`。
- **打包**：`package_type = "python-require"`（纯 Perl 无二进制产物，无 bindirs
  → 无需 `commands.json`）。模块位于 `<site>/Class/Inspector.pm`，site 根为
  `Class/` 的**父级**；`package_info()` 注入 `PERL5LIB`。

> 📌 **版本说明**：本归档为 **1.36**，取自任务提供的源码 URL
> （`.../PLICEASE/Class-Inspector-1.36.tar.gz`，官方 CPAN 可得）。
> 该版本亦为本仓既有 consumer `perl-pod-spell/1.27` 所锚定的版本。

> 📌 **构建系统逐版本不同**：1.36 是普通 MakeMaker（**无 `inc/`**），而 1.30 是
> Module::Install（`inc/` 随包）——不要把一个版本的做法套到另一个版本上。

## 依赖

运行时：`File::Spec >= 0.80` / `base`（perl 核心）；构建：`ExtUtils::MakeMaker`
（perl 核心）；测试：`Test::More >= 0.98`（OHOS perl 自带）。无 Conan 依赖。

## 功能验证

```bash
# 上游测试套件（6 文件 86 用例 = 85 通过 + 1 个 skip 用例；
# 另有 1 个文件因缺 Devel::Hide 整体跳过）
cd Class-Inspector-1.36 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=6, Tests=86, Result: PASS

# 消费者验证（conan create 内 test_package，30 条断言）
conan create archives/c/class-inspector/1.36 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 文档: https://metacpan.org/pod/Class::Inspector
- 发行版: https://metacpan.org/dist/Class-Inspector
- 源码: https://cpan.metacpan.org/authors/id/P/PL/PLICEASE/Class-Inspector-1.36.tar.gz
