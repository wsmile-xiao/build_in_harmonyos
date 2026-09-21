# test-metrics-any 0.01 适配笔记

## 编译环境

- 目标：`aarch64-unknown-linux-ohos`（profile: `ci/conan/profiles/ohos-aarch64`）
- 解释器：`/data/service/hnp/bin/perl` v5.42.0（固定使用，见下「注意事项」）
- conan 2.29.1
- 构建系统：`ExtUtils::MakeMaker`（perl 核心）—— 上游的 `Module::Build` 在 OHOS 不可得

## 本包为何存在

`Test::Metrics::Any` 是 **Metrics::Any 生态的「测试侧」组件**：让使用
`Metrics::Any` 上报指标的库/应用能够**断言**自己确实产生了预期指标。

它与本仓既有的 `metrics-any/0.10` 是**配套对**：

| 包 | 角色 |
|----|------|
| `metrics-any/0.10`（已合入 main / ohpcd） | 指标的**抽象收集**（声明 + 上报） |
| **`test-metrics-any/0.01`**（本包） | 指标的**测试断言**（`is_metrics` / `is_metrics_from`） |

`Test::Metrics::Any` 顶层即 `use Metrics::Any::Adapter 'Test'` 与
`use Metrics::Any::Adapter::Test`（Eager load），因此**运行时依赖
`metrics-any`**——没有它本包连载入都不成立。这也解释了为何二者必须成对适配。

## 编译步骤

```bash
# 1) 取源码 + 校验 sha256（conandata.yml，CPAN 官方 URL）
# 2) build()：生成等价 Makefile.PL（上游 Build.PL 需 Module::Build，OHOS 不可得）
# 3) build()：perl Makefile.PL INSTALLDIRS=site → make → make test（R51 真实运行）
#    → make install DESTDIR=<staging>（测试期 PERL5LIB 注入依赖 metrics-any）
# 4) package()：按登台树原样拷入 package_folder
# 5) package_info()：runenv_info.prepend_path 注入 PERL5LIB
```

## 遇到的问题与解决方案

### 问题 1：首查「是否已适配」时容易误判同类包（R37）

`git ls-tree origin/main | grep 'archives/[mp]/(perl-)?metrics-any/'` 会命中
`archives/m/metrics-any/0.10`——但那是 **`Metrics::Any`（主包）**，与
**`Test::Metrics::Any`（测试助手）** 是**两个不同的 CPAN 发行版**：

- 发行版名：`Metrics-Any` vs `Test-Metrics-Any`
- 模块名：`Metrics::Any::*` vs `Test::Metrics::Any`
- 作者相同（PEVANS）但 tarball 不同

若只看「metrics-any 已有」就下结论，会误判为重复适配而跳过。**判定必须以
CPAN 发行版名 + 模块名双重确认**（本包 `Test-Metrics-Any-0.01`，ohpcd 与 main
均无，属首次适配）。

### 问题 2：Module::Build 不可得 → 生成等价 Makefile.PL

上游 `Build.PL`：

```perl
use Module::Build;
my $build = Module::Build->new(
   module_name => 'Test::Metrics::Any',
   requires => { 'Metrics::Any::Adapter' => 0,
                 'Metrics::Any::Adapter::Test' => 0,
                 'Test::Builder::Module' => 0 },
   configure_requires => { 'Module::Build' => '0.4004' },
   test_requires => { 'Test::More' => '0.88' },
   ...
);
```

**实测**：设备 perl 与 `/data/service/hnp/bin/perl` 的 `@INC` 均无
`Module/Build.pm`，制品仓亦无 `perl-module-build`：

```text
$ /data/service/hnp/bin/perl -MModule::Build -e 1
Can't locate Module/Build.pm in @INC (@INC entries checked: ...)
```

**修法**：`build()` 生成等价 `Makefile.PL`，用 perl 核心的
`ExtUtils::MakeMaker` 驱动，把 `requires`/`test_requires` 逐项转写为
`PREREQ_PM` / `TEST_REQUIRES`（`configure_requires` 的 Module::Build 由
MakeMaker 自身替代，故不列）。**仅新增构建脚本、不改动上游源码**，故
`patches: {}`。（先例：`metrics-any 0.10`、`future 0.52`、`perl-parallel-pipes 0.201`）

### 问题 3（本包关键）：依赖的 `PERL5LIB` 不进 build 上下文

本包 `build()` 内跑 `make test` 时，上游测试要 `use Metrics::Any::Adapter::Test`
——它由运行时依赖 `metrics-any/0.10` 提供。而实测 `metrics-any` 的
`package_info()` **只声明了 `runenv_info`，未声明 `buildenv_info`**：

```python
# metrics-any/0.10/conanfile.py（已合入，不改动）
self.runenv_info.define_path("PERL5LIB", site)   # ← 仅 runenv，无 buildenv
```

因此它的 `PERL5LIB` **不会自动进入本包的 build 上下文**，`make test` 会因
`Can't locate Metrics/Any/Adapter/Test.pm` 失败。若走 `env=["conanbuild"]`
也一样拿不到。

**修法**（不改动已合入的他包配方）：在 `build()` 内遍历依赖包目录，定位其
perl lib 根（`Metrics/Any.pm` 所在目录），显式注入 `PERL5LIB`：

```python
dep_site = self._dep_perl5lib()          # 定位 metrics-any 的 <site>
env_prefix = f'export PERL5LIB="{dep_site}:$PERL5LIB" && '
self.run(env_prefix + "make test", cwd=self.source_folder)
```

### 问题 4：`PERL5LIB` 用 prepend_path 而非 define_path

`metrics-any` 用的是 `define_path`（**覆盖**语义）。本包若也用 `define_path`，
消费方的 `PERL5LIB` 只会是本包那一个，**依赖的取值被丢掉**（`Test::Metrics::Any`
载入后立刻 `use Metrics::Any::Adapter`，就会失败）。

**修法**：本包用 `runenv_info.prepend_path("PERL5LIB", site)`——两者叠加而非
互相覆盖。

### 问题 5：`Test::Builder::Tester` 的行号锚定导致负例误报

消费者测试含 2 个负例（证明 `is_metrics` **真的会失败**、不是恒真空壳）。最初
写法：

```perl
test_out("not ok 1 - should fail");
test_fail(+1);
is_metrics({ a_neg_metric => 999 }, "should fail");
test_test("负例...");
```

**实测反复误报**，根因有两层（读 `Test/Builder/Tester.pm` 源码确认）：

1. `test_fail(+1)` 的语义是「失败发生在**调用点的下一行**」
   （`$line = caller + offset`，见 Tester.pm:230-235）——因此 `test_fail` 与
   被测调用之间**不得插入任何行**（含注释）；
2. `test_err` 会把 `"#     Failed test ($filename at line $line)"` **整行**
   加进期望列表，而实际 stderr 的输出行数与其内部诊断行数不一定对齐
   （实测期望 2 行、实际 3 行），仍失配。

**修法**：负例只断言 **stdout** 并跳过 stderr 比对：

```perl
test_out("not ok 1 - should fail");
is_metrics({ a_neg_metric => 999 }, "should fail");
test_test(name => "负例：值不匹配时 is_metrics 确实失败", skip_err => 1);
```

非空壳性由 `test_out` 充分保证——若 `is_metrics` 是空壳（不报错或报 `ok`），
这里必然拿不到 `not ok` 而失败。

> 附带一处参数传递坑：`test_test("名字", skip_err => 1)` 会让 `%args` 错位
> 解析（3 个元素且首个非 key），表现为测试名丢失（输出 `not ok 14` 无名字）。
> 必须写成 **`test_test(name => "名字", skip_err => 1)`**。

### 问题 6：末尾 `ALL OK` 标记必须按真实结果打印

驱动脚本（`test_test_metrics_any.py`）靠输出里的 `ALL OK` 判定成功。若测试
结束**无条件**打印 `ALL OK`，失败时会骗过该检查（另一种空壳通过形态）。

**修法**：`done_testing()` 之前先取 `Test::More->builder->is_passing`，据此
打印 `ALL OK` 或 `FAILED` 并以非零码退出。

### 问题 7：W3 首次失败——漏了 CI 的 `--build=missing`

首次 `conan create` 报：

```text
ERROR: Missing prebuilt package for 'test-metrics-any/0.01'
```

日志里**完全没有构建阶段**（无 `Calling build` / `RUN:`），说明 conan 直接
去找预编译制品而本包从未构建过。根因是我手写的验证命令漏了 CI 使用的
`--build=missing`（见 `ci/conan/build_and_test.sh:320-322` 的
`CONAN_CREATE_ARGS+=( --build=missing )`）。补上后通过。

> 教训：本地复现 CI 必须**照抄** CI 的完整调用参数，不能只对齐 profile。

## 源码修改

**无**（`patches: {}`）。仅在 `build()` 内新增等价 `Makefile.PL`，不改动上游
任何文件。这使上游 `t/` 套件保持原样运行，也避免升级版本时的补丁冲突。

## 依赖版本

| 包 | 版本 | 类型 | 说明 |
|----|------|------|------|
| metrics-any | 0.10 | requires（运行时） | 提供 `Metrics::Any::Adapter` 与 `::Adapter::Test`；顶层即 `use`，故为运行时依赖 |

其余依赖均为 perl 核心/hnp perl 自带：`Test::Builder::Module`、`Test::More`
（实测 1.302210）。测试期为可选 POD 校验依赖 `Test::Pod` 缺失 → 1 个文件 skip。

## 验证结果

```bash
# 上游测试套件（4 文件 10 用例）
cd Test-Metrics-Any-0.01 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=4, Tests=10, Result: PASS

# 完整本地验证（与 CI 相同 profile + 相同参数）
conan create archives/t/test-metrics-any/0.01 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# → EXIT CODE=0
#   [upstream] Files=4, Tests=10, Result: PASS
#   Package '88092867fbca9f7b190679fa6b23d08222e89586' created
#   test_package: ALL OK - test-metrics-any 0.01 consumer checks passed
```

- 上游测试：**Files=4, Tests=10, Result: PASS**（10/10 = 100%，1 文件因缺可选
  依赖 `Test::Pod` 而 skip，非失败）
- 消费者测试：**15/15 passed**

## 注意事项

1. **固定使用 `/data/service/hnp/bin/perl`（5.42.0）**：与 `metrics-any` /
   `perl-uri` 先例一致，避免设备 perl 与 hnp perl 的 `Errno` 实现差异
   （详见 `metrics-any` notes.md 中 `EWOULDBLOCK`/`ENOTSUP` 的记录）。
2. **依赖注入是必需的**：`metrics-any` 未声明 `buildenv_info`，其 `PERL5LIB`
   不进 build 上下文——本配方在 `build()` 内显式注入。若将来 `metrics-any`
   补上 `buildenv_info`，该注入可简化（但保留亦无害）。
3. **`PERL5LIB` 必须用 `prepend_path`**：依赖用的是 `define_path`（覆盖语义），
   本包若也用 `define_path` 会把依赖的取值挤掉。
4. **负例断言不要用 `test_fail`/`test_err`**：按调用点行号锚定，对本文件任何
   增删行都会误报。用 `test_out` + `test_test(..., skip_err => 1)`。
5. **`test_test` 必须用命名参数**（`name => ...`），否则 `%args` 错位。
6. **本地验证必须带 `--build=missing`**（照抄 CI 参数）。
7. 本包与 `metrics-any` 是配套对：**只在 `test-metrics-any` 内使用
   `Metrics::Any::Adapter::Test`**；`Metrics::Any` 的适配器一旦确定就不能在同
   一进程内更换（上游 `t/10adapter-null.t` 亦为独立文件），消费者若需多适配器
   应分区/分进程测试。
