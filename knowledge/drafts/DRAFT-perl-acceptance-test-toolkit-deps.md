# DRAFT-perl-acceptance-test-toolkit-deps — 验收测试工具集类 CPAN 模块的适配

## 错误特征

两类信号，都不是构建期报错：

**① 上游 t/ 极小（但输出全绿）**

```
t/00use.t .. ok
t/99pod.t .. skipped: Test::Pod 1.00 required for testing POD
All tests successful.
Files=2, Tests=1,  Result: PASS
```

**② 跑验收套件时才暴露「被验收目标缺席」**

```
Can't locate object method "get" via package "0.2" at .../Test/Future/IO/Impl.pm line 572.
```

或（目标模块根本不在 @INC）：

```
Can't locate Future/IO.pm in @INC (you may need to install the Future::IO module)
```

## 触发条件

- 模块定位是**给别人用的验收/一致性测试套件**（`Test::*::Impl`、规范符合性套件等）
- 其导出函数（如 `run_tests @suitenames`）内部调用**被验收目标**的方法
- 阶段：testing —— 上游 t/ 阶段看不出来，只有真跑套件才暴露

## 根因分析

这类模块有两个容易被误判的特征。

### ① 上游 t/ 不代表真实测试面

本包 `t/` 只有 2 个文件：`00use.t`（`require Test::Future::IO::Impl; pass`）与
`99pod.t`（需 `Test::Pod`，本环境跳过）。**实际执行 1 个用例**。

但模块的真实能力是 **13 个验收套件**：

```
run_accept_test     run_connect_test    run_poll_test
run_poll_no_hup_test run_read_test      run_sysread_test
run_recv_test       run_recvfrom_test   run_send_test
run_sleep_test      run_write_test      run_syswrite_test
run_waitpid_test
```

若照上游 t/ 的结果申报「上游测试全过」，等于把「几乎没测」包装成通过 ——
与 R51 要求的真实证据相差甚远。

### ② 真正的依赖是「逻辑依赖」，不在 META prereqs 里

本包的 META prereqs 只声明运行期基础依赖：

```
runtime: Errno / IO::Handle / Socket / Test2::V0 / Time::HiRes / perl >= 5.014
```

全部是 perl 核心模块，**看起来零外部依赖**。但 13 个套件内部全都调用
`Future::IO->sleep/accept/connect/...`：

```perl
sub run_sleep_test {
   time_about sub {
      Future::IO->sleep( 0.2 )->get;      # ← 被验收目标
   }, 0.2, 'Future::IO->sleep( 0.2 ) sleeps 0.2 seconds';
   ...
}
```

因此真正的依赖链是：

```
test-future-io-impl  →（逻辑依赖）→  Future::IO  →  Future
```

`Future::IO` 属于「调用方必须先加载一个实现」的目标：套件用的是
`Future::IO->method`，而不是某个 `Impl::` 子类 —— 实现由调用方通过
`use Future::IO::Impl::MyNewImpl;`（通常配合 `Future::IO->load_impl`）注入。

**后果**：用 META / conan `requires` 都查不出这条依赖（W0/R36 的依赖检查
对它失明），直到真跑套件才报错。本环境实测：hnp perl 无 `Future/IO.pm`，
ohpcd `conan search future-io/*` 为 0，本仓 main 亦无相应归档。

## Recommended Solution

### 主方案（priority 1）— `stub-driven-consumer-test`

**① 上游 t/ 如实申报 + 显式声明覆盖边界**

申报上游的真实数字（2 文件 / 1 用例 / 实际只加载模块），并写明 13 个套件需
调用方先加载被验收实现；该目标在本环境/制品仓/本仓 main 均不可得，属**依赖链
限制**。严禁把套件跳过当通过。

**② 在 test_package 侧用桩实现驱动真实套件**

构造一份被验收目标的**桩实现**（本包为 `Future::IO`）：

```perl
package Future::IO;
sub sleep { return Future::IO::_Stub->new( $_[1] ) }          # 计时未来
sub alarm { return Future::IO::_Stub->new( $_[1] - time() ) }

package Future::IO::_Stub;
sub new        { bless { dur => $_[1], start => time(), cancelled => 0 }, $_[0] }
sub is_ready   { ... }      # 时长耗尽或已取消 → 就绪
sub cancel     { $_[0]->{cancelled} = 1; $_[0] }
sub await      { 睡够剩余时间; $_[0] }
sub get        { $_[0]->await; undef }
```

然后真实驱动**自包含**的套件：

```perl
run_tests 'sleep';      # 选它：不需 socket/pipe/fork，CI 可稳定复现
```

**③ 桩实现须明确标注用途**，避免被误读为「已完成 Future::IO 适配」。

配套断言（本包实测 `1..11`）：

| 来源 | 数量 | 内容 |
|---|---|---|
| 自有 | 5 | 版本；`run_tests` 已导出；13 套件 + `time_about` 齐备；未知套件名必须 die |
| `sleep` 套件 | 6 | `sleep(0.2)` 时长；可 cancel；`->await` 返回 Future；await 后两个 future 均就绪；`alarm(now+0.2)` 时长 |

注意 `run_tests` 的**参数契约**：未知套件名必须 `die`

```perl
my $code = __PACKAGE__->can( "run_${test}_test" )
   or die "Unrecognised test suite name $test";
```

### 回退方案（priority 2）— `blocked-by-dependency-report`

若套件深度依赖真实网络/内核语义、无法用桩驱动，则**包照常构建发布**（它作为
工具本身可用），同时在 notes/manifest 与 result 中如实写明「N 个套件需待被验收
目标适配后由消费方触发」，不发虚假通过率。

### 禁止做法

- ❌ 把套件跳过/不申报，用 1 个加载用例报「上游全过」（R51 口径失真）
- ❌ 把桩实现宣称/报告为「已适配 Future::IO」（会误导依赖方）

## 单库实证（2026-09-18）

| 项 | 实测 |
|---|---|
| 上游 t/（hnp perl 5.42.0）| `Files=2, Tests=1, Result: PASS`（99pod.t skip：需 Test::Pod）|
| 消费者（桩驱动 `run_tests 'sleep'`）| `1..11` 全过 |
| `Future::IO` 可得性 | hnp perl ❌ / ohpcd `conan search future-io/*` → 0 ❌ / 本仓 main ❌ |

## 测试覆盖边界

- 本条解决的是「验收工具类模块如何如实申报 + 如何在依赖缺席时仍验证真实行为」。
- **未**解决 `Future::IO` 及其实现的适配 —— 那是独立工作项（依赖链
  `Future::IO → Future`，其中 `Future` 已有适配在途）。
- 若某模块的套件**无法**用桩驱动（真实网络语义等），适用回退方案，不要为了
  "有断言"而用桩伪造出与真实实现无关的结论。

## 关联条目

- 相似：`E155`（纯 Perl + MakeMaker 构建需 `PERL5LIB`）
- 相关：`DRAFT-perl-module-build-makemaker-substitution`（同属 CPAN 纯 Perl 适配这一类）
