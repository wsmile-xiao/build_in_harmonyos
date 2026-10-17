# metrics-any

[Metrics::Any](https://metacpan.org/pod/Metrics::Any) — 监控指标的**抽象收集**
机制（Perl）。模块作者在代码中声明并上报指标，实际落盘委托给可配置的 adapter。

## 简介

设计灵感来自 `Log::Any`：库代码只负责「声明 + 上报」，应用层决定指标去向。

| 模块 | 用途 |
|------|------|
| `Metrics::Any` | 主模块，`use Metrics::Any '$metrics'` 获取全局句柄 |
| `Metrics::Any::Collector` | 指标注册与上报 API（`make_*` / `inc_*` / `report_*` / `set_*`）|
| `Metrics::Any::Adapter` | 适配器基类与加载入口 |
| `Metrics::Any::Adapter::Null` | 丢弃全部指标（用于禁用）|
| `Metrics::Any::Adapter::File` | 写入文件句柄（测试/调试用）|
| `Metrics::Any::Adapter::Stderr` | 写入 STDERR |
| `Metrics::Any::Adapter::Tee` | 同时转发给多个适配器 |
| `Metrics::Any::Adapter::Test` | 供单元测试断言指标内容 |
| `Metrics::Any::AdapterBase::Stored` | 存储型适配器基类（供自定义子类化）|

指标类型：**counter**（累加计数）、**distribution**（分布：count + total）、
**gauge**（可增可减可直设）、**timer**（时长统计）。支持 label 维度。

## OHOS 适配

- **纯 Perl 模块**：无 XS、无 C/C++ 编译、无平台相关代码，行为与上游一致。
- **构建系统替换**：上游以 `Module::Build`（`Build.PL`）为构建系统，而 OHOS
  环境不带该模块（设备 perl 5.42.2 与 `/data/service/hnp/bin/perl` 5.42.0 均无
  `Module/Build.pm`，制品仓也无 `perl-module-build` 制品）。配方在 `build()` 中
  用 perl 核心模块 `ExtUtils::MakeMaker` 生成**等价 Makefile.PL**（逐项转写上游
  `Build.PL` 的 `module_name`/`requires`/`test_requires`）。
- **零补丁**：仅新增构建脚本，未改动任何上游源码，故 `patches: {}`。
- **打包**：`package_type = "python-require"`（纯 Perl 无二进制产物，无 bindirs
  → 无需 `commands.json`）。模块位于 `<site>/Metrics/Any.pm`，故 site 根为
  `Metrics/` 的**父级**；`package_info()` 注入 `PERL5LIB` 供下游
  `use Metrics::Any`。

> ⚠️ **解释器要求**：配方固定使用 `/data/service/hnp/bin/perl`（5.42.0）。
> 设备 perl 5.42.2 的 `Errno` 未导出 `EWOULDBLOCK` / `ENOTSUP`（与
> `EAGAIN` / `EOPNOTSUPP` 同值的别名被去重），会使上游 `t/11adapter-file.t`
> 在编译期失败。

## 依赖

运行时依赖全部为 perl 核心模块：`perl >= 5.014`、`List::Util >= 1.29`；
测试依赖 `Test2::V0`（OHOS perl 自带）。无 Conan 依赖。

## 功能验证

```bash
# 上游测试套件（14 文件 83 用例）
cd Metrics-Any-0.10 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=14, Tests=83, Result: PASS

# 消费者验证（conan create 内 test_package，24 项断言）
conan create archives/m/metrics-any/0.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 文档: https://metacpan.org/pod/Metrics::Any
- 发行版: https://metacpan.org/dist/Metrics-Any
- 源码: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Metrics-Any-0.10.tar.gz
