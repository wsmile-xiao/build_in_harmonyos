# future-queue 0.52 适配笔记

## 编译环境

- 目标：`aarch64-unknown-linux-ohos`（profile: `ci/conan/profiles/ohos-aarch64`）
- 解释器：`/data/service/hnp/bin/perl` v5.42.0（固定使用，见「注意事项」）
- conan 2.29.1
- 构建系统：`ExtUtils::MakeMaker`（perl 核心）—— 上游的 `Module::Build` 在 OHOS 不可得

## 本包为何存在

`Future::Queue` 提供**基于 Future 的 FIFO 队列**：生产者 `push` 值、消费者
`shift` 值；队列空时 `shift` 返回一个**尚未完成**的 Future，稍后 `push` 使其
完成。用于把异步事件流串行化。

它与本仓既有的 `future` 0.52 是**配套对**：

| 包 | 角色 |
|----|------|
| `future` 0.52（已合入 main / ohpcd） | Future 的**基类与基本组合子**（done/fail/then 等） |
| **`future-queue` 0.52**（本包） | 在其上构建的**队列抽象**（push/shift 背压语义） |

`Future::Queue` 顶部即 `use Future;`，`shift` 的返回值就是 `Future` 实例 ——
没有 `future` 本包不成立。

## 编译步骤

```bash
# 1) 取源码 + 校验 sha256（conandata.yml，CPAN 官方 URL）
# 2) build()：生成等价 Makefile.PL（上游 Build.PL 需 Module::Build，OHOS 不可得）
# 3) build()：perl Makefile.PL INSTALLDIRS=site → make → make test（R51 真实运行）
#    → make install DESTDIR=<staging>（测试期 PERL5LIB 注入 future 依赖）
# 4) package()：按登台树原样拷入 package_folder
# 5) package_info()：runenv_info.prepend_path 注入 PERL5LIB
```

## 遇到的问题与解决方案

### 问题 1：Module::Build 不可得 → 生成等价 Makefile.PL

上游 `Build.PL`：

```perl
my $build = Module::Build->new(
   module_name => 'Future::Queue',
   requires => { 'perl' => '5.014', 'Future' => 0 },
   test_requires => { 'Test2::V0' => 0 },
   configure_requires => { 'Module::Build' => '0.4004' },
   ...
);
```

**实测**：hnp perl 的 `@INC` 无 `Module/Build.pm`，制品仓亦无
`perl-module-build` → 无法用上游构建脚本。**修法**：`build()` 生成等价
`Makefile.PL`，把 `requires`/`test_requires` 逐项转写为
`PREREQ_PM` / `TEST_REQUIRES`（`configure_requires` 的 Module::Build 由
MakeMaker 自身替代）。**仅新增构建脚本、不改动上游源码**，故 `patches: {}`。
（先例：`metrics-any 0.10`、`test-metrics-any 0.01`）

### 问题 2：依赖的 `PERL5LIB` 不进 build 上下文

`build()` 内跑 `make test` 时，`t/01queue.t` 等需要 `use Future`。而
`future/0.52` 的 `package_info()` **只声明了 `runenv_info`**：

```python
# future/0.52/conanfile.py:136（已合入，不改动）
self.runenv_info.define_path("PERL5LIB", site)
```

未声明 `buildenv_info` → 其 `PERL5LIB` 不会进入本包 build 上下文。**修法**：
`build()` 内遍历依赖包目录定位其 perl lib 根并显式注入（不改动已合入的
`future` 配方，R21）。

### 问题 3：消费者测试里 `await` 不可用

最初按直觉写 `use Future qw(await);`，实测报：

```text
Attempt to call undefined import method with arguments ("await") via package
"Future"
Can't locate object method "await" via package "Future::Queue"
```

**Future 并未导出 `await`**（它是 `Future::PP` 等内部的等待实现，不对外导出）。
**修法**：照抄上游 `t/` 的惯用法——直接 `$future->result` 取已就绪的值，配
`is_done` / `is_ready` 判状态，完全不使用 `await`。

### 问题 4：`package_info` 用 `prepend_path` 而非 `define_path`

依赖用的是覆盖语义的 `define_path`。本包若也用它，消费方的 `PERL5LIB` 只会剩
本包一条，`use Future::Queue` 后紧跟的 `use Future` 将解析不到。故用
`prepend_path` 追加。

### 问题 5：上游 `t/99pod.t` 因缺 `Test::Pod` skip（如实申报）

`t/99pod.t` 执行 `eval "use Test::Pod 1.00"`，而 `Test::Pod` 在
ohpcd / main / hnp perl **均不可得** → 该文件 skip。

**重要事实**：`Test::Pod` **并未**出现在本包 `META.json` 的 prereqs 中——
上游自己也**没有**把它声明为依赖，属"未声明的可选检查"。

**处置（经与用户确认）**：`Test::Pod` 是几十个 perl 包的**共性缺口**，作为
**独立任务另行适配**（其依赖 Test::More / Pod::Simple / Test::Builder::Tester
等已全部由 hnp perl 满足，适配成本低）。本 PR：
- **不**以 `ignore` / `deselect` / allowlist 规避或掩盖该用例；
- 如实记录 skip 原因（本 notes 与 `test_package/MANIFEST.yml`）；
- 保留套件退出码作为构建门（非 0 即失败）。

### 问题 6：本地验证必须照抄 CI 参数

首次 `conan create` 若漏 `--build=missing` 会报
`Missing prebuilt package for 'future-queue/0.52'`（且日志里完全没有构建阶段）。
CI 的调用见 `ci/conan/build_and_test.sh:320-322`。

## 源码修改

**无**（`patches: {}`）。仅在 `build()` 内新增等价 `Makefile.PL`，不改动上游
任何文件。

## 依赖版本

| 包 | 版本 | 类型 | 说明 |
|----|------|------|------|
| future | 0.52 | requires（运行时） | 队列的 shift 返回 Future、push 背压返回 Future，需该模块 |

其余为 perl 核心/hnp perl 自带：`Test2::V0`（实测 1.302210）。

## 验证结果

```bash
# 上游测试套件
cd Future-Queue-0.52 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=7, Tests=35, Result: PASS

# 完整本地验证（与 CI 相同 profile + 相同参数）
conan create archives/f/future-queue/0.52 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
# → EXIT CODE=0
#   [upstream] Files=7, Tests=35, Result: PASS
#   Package '9260a1f945c634c05a5922a80db2a78961322747' created
#   ALL OK - future-queue 0.52 consumer checks passed
```

- 上游测试：**Files=7, Tests=35, Result: PASS**（35/35 = 100%；99pod.t skip 见问题 5）
- 消费者测试：**27/27 passed**

## 注意事项

1. **固定使用 `/data/service/hnp/bin/perl`（5.42.0）**：与 `metrics-any` /
   `future` 先例一致，避免设备 perl 与 hnp perl 的 `Errno` 实现差异。
2. **依赖注入必需**：`future` 未声明 `buildenv_info`，`build()` 内需显式注入
   `PERL5LIB`，否则 `use Future` 失败。
3. **不要用 `await`**：Future 未导出它；用 `$f->result` + `is_done`/`is_ready`
   （上游 `t/` 同款）。
4. **`PERL5LIB` 用 `prepend_path`**：依赖用 `define_path`（覆盖语义）。
5. **本地验证带 `--build=missing`**（照抄 CI 参数）。
6. 本包与 `future` 是配套对；`99pod.t` 的 skip 是已知共性缺口，另行适配
   `Test::Pod` 后可移除该 skip。
