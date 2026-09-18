# metrics-any 0.10 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（上游 Module::Build → 适配为 ExtUtils::MakeMaker）
- **编译日期**: 2026-09-18
- **平台**: arm64-ohos（OpenHarmony PC）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（不改动上游源码；Makefile.PL 为新增构建脚本）

## 软件简介

Metrics::Any 提供「监控指标抽象收集」机制：模块作者在代码中声明并上报指标
（counter / distribution / gauge / timer），实际落盘委托给可配置的 adapter。
设计灵感来自 Log::Any。随包模块：

| 模块 | 说明 |
|------|------|
| `Metrics::Any` | 主模块，`use Metrics::Any '$metrics'` 取全局句柄 |
| `Metrics::Any::Collector` | 指标注册与上报 API（make_*/inc_*/report_*）|
| `Metrics::Any::Adapter` | 适配器基类 + 加载入口 |
| `Metrics::Any::Adapter::{Null,File,Stderr,Tee,Test}` | 各落盘适配器 |
| `Metrics::Any::AdapterBase::Stored` | 存储型适配器基类（供自定义子类化）|

## 编译步骤（conan create 全流程）

```bash
conan create archives/m/metrics-any/0.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Metrics-Any-0.10）。

### 2. 构建（build()）——核心适配点

上游构建系统是 **Module::Build**（`Build.PL`，configure_requires
`Module::Build >= 0.4004`），OHOS 不可得（设备 perl 5.42.2 与 hnp perl 5.42.0
均无 `Module/Build.pm`；制品仓 `conan search perl-module-build/*` 为 0 个）。

对策：**用 perl 核心 ExtUtils::MakeMaker 生成等价 Makefile.PL**，逐项转写
上游 Build.PL 的 `module_name` / `requires` / `test_requires`：

```perl
WriteMakefile(
    NAME             => 'Metrics::Any',
    VERSION_FROM     => 'lib/Metrics/Any.pm',
    LICENSE          => 'perl_5',
    MIN_PERL_VERSION => '5.014',
    PREREQ_PM        => { 'List::Util' => '1.29', 'perl' => '5.014' },
    TEST_REQUIRES    => { 'Test2::V0' => 0 },
    NO_MYMETA        => 1,
);
```

随后 `perl Makefile.PL INSTALLDIRS=site` → `make` → `make test` →
`make install DESTDIR=<staging>`。

### 3. 打包（package()）
- 按登台树原样拷入 package_folder
- **site 目录定位必须回溯父级**（本次踩坑，见下）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 的 test 阶段报 `missing packaged module: .../site_perl/5.42.0/Metrics/Metrics/Any.pm` | `_site_dir()` 遍历到 `Any.pm` 所在目录后**直接返回了 `Metrics/` 目录本身**，而模块路径是 `<site>/Metrics/Any.pm` —— site 根应是其**父级** | `_site_dir()` / test_package 均改为返回 `os.path.dirname(root)`；修正后 24 项断言全过 |
| 2 | 上游 `t/11adapter-file.t` 在**设备 perl 5.42.2** 下编译失败：`"EWOULDBLOCK" is not exported by the Errno module` | 设备 perl 5.42.2 的 `Errno.pm` 把与 `EAGAIN` 同值的别名 `EWOULDBLOCK`（及 `ENOTSUP`）**去重丢弃**，未进 `@EXPORT_OK`；OHOS 预装 `/data/service/hnp/bin/perl` 5.42.0 的 Errno 完整 | 配方与 test_package **统一固定 hnp perl**（与仓内 perl-uri、perl-io-multiplex 先例一致）；hnp perl 下同套件 14 文件 83 用例全过 |
| 3 | 消费者断言 `$metrics appears false with Null adapter` 在同进程内失败 | Metrics::Any 的适配器**一旦确定就不能在同一进程内更换** —— 已激活 Test 适配器后再 `use Metrics::Any::Adapter 'Null'` 不生效 | 把 Null 适配器断言拆成**独立进程**脚本 `test_metrics_any_null.pl`（与上游 `t/10adapter-null.t` 独立 .t 的运行模型一致）|

## 依赖

| 类型 | 依赖 | 状态 |
|---|---|---|
| runtime | perl>=5.014 / List::Util>=1.29 | 均为 perl 核心模块，OHOS perl 内建 ✅ |
| configure | Module::Build>=0.4004 | **OHOS 不可得** → MakeMaker 替代 ✅ |
| test | Test2::V0 | OHOS perl 自带 ✅ |
| Conan | 无 | — |

## 上游测试（R51 申报表）

| 项 | 内容 |
|---|---|
| 测试清点 | `t/` 目录 **14 个 .t 文件** |
| 运行方式 | `make test`（MakeMaker 的 test 目标驱动 TAP::Harness） |
| 实测结果 | **Files=14, Tests=83, Result: PASS**，失败 0 |
| 跳过项 | **1 个**：`99pod.t`（`Test::Pod 1.00 required for testing POD`，可选依赖缺失）|
| 是否入 build | **是**（`upstream_test_in_build: true`）|
| 上游测试改动 | **无**（原样运行）|

## 验证结果

```bash
# conan create（含 test_package R34 消费者验证）——rc=0
conan create archives/m/metrics-any/0.10 -pr:h=... -pr:b=... --build=missing
metrics-any/0.10: package(): Packaged 9 '.pm' files
metrics-any/0.10: Created package revision 0aafdab39081961dbd41aceaac7ea94d
metrics-any/0.10: PERL5LIB=.../site_perl/5.42.0
...
ok - Metrics::Any version is 0.10
...（24 项断言，分两个独立进程）
ALL OK
OK: metrics-any 0.10 python-driven consumer check
```

test_package 消费者测试覆盖（24 项断言，全过）：版本号、`$metrics` 全局句柄、
counter 聚合与 ARRAYref/HASHref 两种标签传参、gauge 三态（inc/inc_by/set_to）、
distribution count/total 累计、timer、strict 模式的重复注册与未注册上报必须失败、
Null 适配器下全 API 静默可用与真假语义、`AdapterBase::Stored` 与全部子模块随包安装。

## 注意事项

- 纯 Perl 包不涉及交叉编译工具链；`make` 使用宿主 perl 即可（OHOS 上即目标平台原生）。
- **解释器必须固定 hnp perl**：见上表问题 #2，设备 perl 的 Errno 别名去重会让
  上游测试假失败。
- Makefile.PL 的 `ABSTRACT_FROM` 可能告警 `Setting ABSTRACT via file ... failed`，
  无害、不影响产物。

## 对话记录

### 对话 #1（2026-09-18）

- 在鸿蒙 aarch64 设备上完成适配：`conan create` 通过。
- 上游测试真实运行：t/ 14 文件 83 用例全过（1 skip 为 Test::Pod 可选依赖）。
- 消费者测试 24/24 通过，覆盖 Test 与 Null 两类适配器。
- 零补丁：未改动上游源码，仅新增等价 Makefile.PL。
- 本次三处实测教训已记入 manifest 的 knowledge_gained：①site 目录需回溯父级；
  ②设备 perl Errno 别名去重须固定 hnp perl；③适配器不可同进程更换，Null 断言
  需独立进程。
---

**编译结束**: 2026-09-18 04:02
**最终状态**: built
