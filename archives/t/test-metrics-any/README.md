# test-metrics-any

[Test::Metrics::Any](https://metacpan.org/pod/Test::Metrics::Any) — 断言测试
工具（Perl）：断言某段代码**确实产生了**预期的监控指标。是
[Metrics::Any](https://metacpan.org/pod/Metrics::Any) 生态的「测试侧」组件。

## 简介

以 `Test::Builder::Module` 为基类，导出两个断言函数：

| 导出符号 | 用途 |
|----------|------|
| `is_metrics( \%expect, $name )` | 断言指标当前值等于给定值（或满足谓词） |
| `is_metrics_from( sub {...}, \%expect, $name )` | 断言代码块执行**产生**了给定指标 |

指标名格式与 `Metrics::Any::Adapter::Test` 一致：组件以 `_` 连接，标签以
空格追加为 `name:value`，例如 `"a_labelled_metric label:here"`。

**谓词助手**（**不在 `@EXPORT` 中**，需全限定调用
`Test::Metrics::Any::positive`，上游 `t/02predicates.t` 亦如此）：

| 谓词 | 语义 |
|------|------|
| `positive()` | 值 > 0 |
| `at_least($n)` | 值 >= $n |
| `greater_than($n)` | 值 > $n |

语义特点：`is_metrics` **只校验哈希中提到的指标**——被测代码上报了额外指标
**不算失败**，便于新增指标时不破坏既有测试。

## OHOS 适配

- **纯 Perl 单模块**（`lib/Test/Metrics/Any.pm`）：无 XS、无 C/C++ 编译、无
  平台相关代码，行为与上游一致。
- **构建系统替换**：上游以 `Module::Build`（`Build.PL`）为构建系统，而 OHOS
  环境不带该模块（设备 perl 与 `/data/service/hnp/bin/perl` 均无
  `Module/Build.pm`，制品仓也无 `perl-module-build` 制品）。配方在 `build()` 中
  用 perl 核心模块 `ExtUtils::MakeMaker` 生成**等价 Makefile.PL**（逐项转写上游
  `Build.PL` 的 `module_name`/`requires`/`test_requires`）。
- **零补丁**：仅新增构建脚本，未改动任何上游源码，故 `patches: {}`。
- **打包**：`package_type = "python-require"`（纯 Perl 无二进制产物，无 bindirs
  → 无需 `commands.json`）。模块位于 `<site>/Test/Metrics/Any.pm`，故 site 根为
  `Test/` 的**父级**；`package_info()` 注入 `PERL5LIB` 供下游
  `use Test::Metrics::Any`。

> ⚠️ **依赖注入**：`metrics-any` 的 `package_info()` 只声明了 `runenv_info`
> （未声明 `buildenv_info`），其 `PERL5LIB` 不会自动进入本包的 build 上下文，
> 而本包 `build()` 内跑 `make test` 需要它。配方在 `build()` 内显式定位依赖的
> perl lib 根并注入 `PERL5LIB`（不改动已合入的 `metrics-any` 配方）。
> 另外本包用 **`prepend_path`** 而非 `define_path`：依赖用的是覆盖语义的
> `define_path`，若本包也用 `define_path` 会把依赖的取值挤掉。

## 依赖

| 包 | 版本 | 类型 | 说明 |
|----|------|------|------|
| **metrics-any** | 0.10 | 运行时（Conan） | 提供 `Metrics::Any::Adapter` 与 `Metrics::Any::Adapter::Test`；本模块顶层即 `use`，故为运行时依赖 |

其余为 perl 核心/hnp perl 自带：`Test::Builder::Module`、`Test::More`。
可选 POD 校验依赖 `Test::Pod` 缺失 → 上游 1 个测试文件 skip（非失败）。

## 功能验证

```bash
# 上游测试套件（4 文件 10 用例）
cd Test-Metrics-Any-0.01 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=4, Tests=10, Result: PASS

# 消费者验证（conan create 内 test_package，15 项断言）
conan create archives/t/test-metrics-any/0.01 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 文档: https://metacpan.org/pod/Test::Metrics::Any
- 发行版: https://metacpan.org/dist/Test-Metrics-Any
- 源码: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Test-Metrics-Any-0.01.tar.gz
- 配套包: [`metrics-any`](../metrics-any/README.md)（指标的抽象收集）
