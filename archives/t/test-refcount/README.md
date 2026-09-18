# test-refcount

[Test::Refcount](https://metacpan.org/pod/Test::Refcount) — 断言 Perl 变量
**引用计数**的测试辅助模块。

## 简介

引用计数是 Perl 对象 `DESTROY` 时机的关键：如果某对象在构造后仍有 2 个引用，
说明有地方泄漏了引用。Test::Refcount 让测试可以直接断言引用数：

| 函数 | 导出方式 | 说明 |
|------|---------|------|
| `is_refcount( $obj, $count, $name )` | `@EXPORT` | 断言 `$obj` 有 `$count` 个引用 |
| `is_oneref( $obj, $name )` | `@EXPORT` | 断言 `$obj` 只有 1 个引用 |
| `refcount( $obj )` | **`@EXPORT_OK`** | 返回引用数（0.09 新增），用于「先记录再比对」的测试 |

```perl
use Test::More tests => 2;
use Test::Refcount;                     # is_refcount / is_oneref 默认导入

my $ball = MyBall->new();
is_oneref( $ball, 'One reference after construct' );

$ball->bounce;

is_oneref( $ball, 'One reference just before EOF' );
```

`refcount()` 在 `@EXPORT_OK`，须按上游 POD 形式显式导入：

```perl
use Test::Refcount import => [qw( is_refcount refcount )];
```

> ⚠️ 对继承 `Test::Builder::Module` 的模块（Test::Refcount、Test::More 同族），
> **不能**写 `use Test::Refcount qw( refcount )` —— `import` 的位置参数会被当作
> plan 参数，编译期报 `plan() doesn't understand refcount`。

失败时给出诊断 `#   expected N references, found M`；若安装了可选增强
`Devel::MAT` / `Devel::FindRef`，还会附堆转储与引用链（缺失时自动降级）。

## OHOS 适配

- **纯 Perl 模块**：无 XS、无 C/C++ 编译、无平台相关代码，行为与上游一致；
  依赖的 `B`（引用计数内省）与 `Scalar::Util` 均为 perl 核心模块。
- **构建系统替换**：上游以 `Module::Build`（`Build.PL`）为构建系统，而 OHOS
  环境不带该模块（设备 perl 5.42.2 与 `/data/service/hnp/bin/perl` 5.42.0 均无
  `Module/Build.pm`，制品仓也无 `perl-module-build` 制品）。配方在 `build()` 中
  用 perl 核心模块 `ExtUtils::MakeMaker` 生成**等价 Makefile.PL**。
- **可选依赖不硬绑**：上游 `recommends => { Devel::MAT => 0.04 }` 为可选增强，
  **未**写入 `PREREQ_PM`（缺失时模块按 `HAVE_DEVEL_MAT_DUMPER=0` 降级，上游
  测试亦按该常量分支）。
- **零补丁**：仅新增构建脚本，未改动任何上游源码，故 `patches: {}`。
- **打包**：`package_type = "python-require"`（纯 Perl 无二进制产物，无 bindirs
  → 无需 `commands.json`）。模块位于 `<site>/Test/Refcount.pm`，故 site 根为
  `Test/` 的**父级**；`package_info()` 注入 `PERL5LIB` 供下游 `use Test::Refcount`。

## 依赖

运行时：`B` / `Scalar::Util` / `Test::Builder`（均为 perl 核心模块）；
测试：`Test::Builder::Tester` / `Test::More >= 0.88`（OHOS perl 自带）。
无 Conan 依赖。

## 功能验证

```bash
# 上游测试套件（6 文件 20 用例）
cd Test-Refcount-0.10 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=6, Tests=20, Result: PASS

# 消费者验证（conan create 内 test_package，16 条断言）
conan create archives/t/test-refcount/0.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 文档: https://metacpan.org/pod/Test::Refcount
- 发行版: https://metacpan.org/dist/Test-Refcount
- 源码: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Test-Refcount-0.10.tar.gz
