# DRAFT-perl-makefile-gated-test-skip-all — 上游测试以「存在 Makefile」为运行前提时只能走 make test

## 错误特征

**没有报错**——这正是它危险的地方。裸 `prove` 会给出一个看起来正常的绿色结果：

```
t/00-report-prereqs.t .. ok
All tests successful.
Files=4, Tests=1,  1 wallclock secs
Result: PASS
```

对照同一套件经 `make test`：

```
All tests successful.
Files=4, Tests=39,  6 wallclock secs
Result: PASS
```

文件数一样（4），**用例数从 39 掉到 1** —— 3 个文件被整体 skip，但汇总行仍写
"All tests successful"。若只看这句话就申报，等于把「测试基本没跑」当成通过。

被 skip 的文件开头都有同样的守卫：

```perl
plan skip_all => 'This test requires a Makefile in the built distribution'
    if not -f 'Makefile';
```

## 触发条件

- 上游测试以**构建产物存在性**为运行前提（`-f 'Makefile'`、`-f blib/...`、`-d build/`）
- 用裸 `prove -Ilib t/`（或直接 `perl t/xxx.t`）在源码目录运行，未先生成 Makefile
- 阶段：testing —— 通常发生在本地快速验证或配方未把 `make test` 纳入 build() 时

## 根因分析

这类测试的**被测对象不是模块本身，而是构建/安装行为**，因此必须有一个真实
Makefile 才能跑。典型形态（File-ShareDir-Install 0.14 的 t/10_makefile.t）：

1. 文件开头 `plan skip_all ... if not -f 'Makefile'`
2. 用模块 API 登记待安装内容（`install_share` 等）
3. 调用 `WriteMakefile` 生成一个测试用 Makefile
4. **递归调用 `$Config{make}`** 执行它
5. 断言 blib 中的产物（文件是否被复制、隐藏文件是否被排除等）

没有 Makefile → 第 1 步直接整体 skip。`prove` 统计的是「文件数」，
skip 的文件仍计入 `Files=`，所以 `Files=4` 看起来正常，只有 `Tests=` 暴露真相。

## Recommended Solution

### 主方案（priority 1）— `run-via-generated-makefile`

1. 本地/配方中统一经 `make test` 运行：

```bash
perl Makefile.PL INSTALLDIRS=site && make && make test
```

2. 把 `make test` 放进 conanfile.py 的 `build()`，使其成为构建期真实门禁
   （与 R51 的「上游测试真实运行」一致）：

```python
self.run(f"{perl} Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
self.run("make", cwd=self.source_folder)
self.run("make test", cwd=self.source_folder)   # 不要换成裸 prove
```

3. **申报前核对 `Tests=` 数值**：与 `prove` 结果或历史数据差异巨大 → 先查
   是不是 skip_all 前提没满足。

### 回退方案（priority 2）— `assert-no-skip`

若确因构建隔离等原因只能裸 prove，则必须显式量化 skip 面并在申报中说明：

```bash
prove -Ilib t/ 2>&1 | grep -c skipped
```

**不得**把缩减后的分母当上游测试通过率；用 test_package 的消费者断言补齐
真实行为验证。

### 禁止做法

- ❌ 把 skip 掉大半的裸 prove 结果当上游测试通过率申报（分母失真，违反 R51）
- ❌ `sed -i` 删掉 `plan skip_all` 让测试"跑起来"（绕过其依赖的构建前提，结果不可信）
- ❌ 只看 `All tests successful.` 就收工，不核对 `Files=` / `Tests=`

## 单库实证（2026-09-18）

| 库 | 运行方式 | 结果 |
|---|---|---|
| File-ShareDir-Install 0.14 | 裸 `prove -Ilib t/` | `Files=4, Tests=1`（3 文件 skip）—— 假绿 |
| File-ShareDir-Install 0.14 | `make test`（配方 build() 内）| `Files=4, Tests=39, Result: PASS` |

## 测试覆盖边界

- 本条针对「以 Makefile/blib 存在性为前提」的 skip_all。若测试 skip 是因为
  **可选功能依赖缺失**（如缺 `Test::Pod`、缺 XS 后端），属于正常 skip，不适用本条。
- 判别口径：看 skip 的理由文本——`'This test requires a Makefile...'` 一类
  「缺构建产物」属本条；`'Test::Pod 1.00 required'` 一类「缺可选模块」属正常。
- 若上游测试**在 make test 下也失败**，那是真实适配问题，不属本条。

## 关联条目

- 相似：`E155`（纯 Perl + MakeMaker 构建需 `PERL5LIB` 补路径）
- 相关：`DRAFT-perl-module-build-makemaker-substitution`（同属 CPAN 纯 Perl 适配这一类）
