# test-future-io-impl 0.21 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（上游 Module::Build → 适配为 ExtUtils::MakeMaker）
- **编译日期**: 2026-09-18
- **平台**: arm64-ohos（OpenHarmony PC），perl 5.42.0（/data/service/hnp）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（不改动上游源码；Makefile.PL 为新增构建脚本）

## 软件简介

Test::Future::IO::Impl 是 **Future::IO 实现方的验收测试工具集**：导出
`run_tests @suitenames`，由实现包在自己的测试中调用，以验证 accept/connect/
read/recv/send/sleep/write/waitpid/poll 等行为符合规范。单模块
`lib/Test/Future/IO/Impl.pm`（798 行），纯 Perl。

| 符号 | 导出 | 说明 |
|------|------|------|
| `run_tests @suitenames` | `@EXPORT` | 按套件名分发执行验收测试；未知套件名 die |
| `time_about(&\@)` | — | 计时断言助手（窗口 0.9×~1.5×，实现方自测用）|

**13 个验收套件**：`accept` / `connect` / `poll` / `poll_no_hup` / `read` /
`sysread` / `recv` / `recvfrom` / `send` / `sleep` / `write` / `syswrite` /
`waitpid`。

```perl
# 实现方的测试脚本
use Test::More;
use Test::Future::IO::Impl;
use Future::IO::Impl::MyNewImpl;    # ← 必须先加载一个实现

run_tests 'sleep';
done_testing;
```

## 编译步骤（conan create 全流程）

```bash
conan create archives/t/test-future-io-impl/0.21 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Test-Future-IO-Impl-0.21）。

### 2. 构建（build()）——核心适配点

上游构建系统是 **Module::Build**（`Build.PL`，configure_requires
`Module::Build >= 0.4004`），OHOS 不可得（设备 perl 与 hnp perl 均无
`Module/Build.pm`；制品仓 `conan search perl-module-build/*` 为 0 个）。

对策：**用 perl 核心 ExtUtils::MakeMaker 生成等价 Makefile.PL**，逐项转写
上游 Build.PL 的 `module_name` / `requires`（与 META.json 的 prereqs 对齐）：

```perl
WriteMakefile(
    NAME             => 'Test::Future::IO::Impl',
    VERSION_FROM     => 'lib/Test/Future/IO/Impl.pm',
    LICENSE          => 'perl_5',
    MIN_PERL_VERSION => '5.014',
    PREREQ_PM        => { Errno=>0, 'IO::Handle'=>0, Socket=>0,
                          'Time::HiRes'=>0, 'Test2::V0'=>0, perl=>'5.014' },
    NO_MYMETA        => 1,
);
```

随后 `perl Makefile.PL INSTALLDIRS=site` → `make` → `make test` →
`make install DESTDIR=<staging>`。

### 3. 打包（package()）
- 按登台树原样拷入 package_folder
- 以遍历定位 `Test/Future/IO/Impl.pm` 后**上溯三级**得到 site 目录
  （模块相对路径为三层，沿用 metrics-any / test-refcount /
  file-sharedir-install 的教训，不可返回末级目录）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者脚本报 `Can't locate object method "get" via package "0.2"` | 桩实现的构造写成 `Future::IO::_Stub::new($dur)`（函数式调用），把**时长当成类名** | 改为 `Future::IO::_Stub->new($dur)` 方法调用；后续断言全过 |
| 2 | `run_tests` 无法直接实跑：所有套件都调用 `Future::IO->...` | 本模块是**验收工具集**，必须由调用方先加载一个 Future::IO 实现；而 Future::IO 在 hnp perl 与 ohpcd 中均不存在 | 消费者脚本内置一份 Future::IO 桩实现（sleep/alarm + future 的 get/cancel/await/is_ready），据以真实驱动自包含的 `sleep` 套件 |
| 3 | 上游 t/ 仅 1 个可执行用例，看不出模块真实能力 | 上游测试只做 `require` 加载；13 个套件属「由实现方调用」的公共 API，不在自身 t/ 内触发 | 在消费者侧补齐：既核验 13 套件齐备 + 未知套件名 die，又实跑 sleep 套件 6 项断言 |

## 依赖

| 类型 | 依赖 | 状态 |
|---|---|---|
| runtime（META） | Errno / IO::Handle / Socket / Time::HiRes / Test2::V0 | 均为 perl 核心或环境已有，hnp perl 内建 ✅ |
| runtime（逻辑）| **Future::IO 及其实现**（run_tests 的被验收目标）| ❌ 本环境与 ohpcd 均无；本仓 main 无归档。13 套件实跑待该依赖链适配后由消费方触发 |
| configure | Module::Build >= 0.4004 | **OHOS 不可得** → MakeMaker 替代 ✅ |
| Conan | 无 | — |

> **依赖链说明**：`Future::IO` → `Future`；仓内 `future/0.52` 尚在 PR 阶段
> （未合入 main）。本包本身**可独立构建与安装**，只是其 13 个验收套件需要
> 目标实现才能运行——这属逻辑依赖，不影响本包作为工具的可用性。

## 上游测试（R51 申报表）

| 项 | 内容 |
|---|---|
| 测试清点 | `t/` 目录 **2 个 .t 文件** |
| 运行方式 | `make test`（MakeMaker 的 test 目标驱动 TAP::Harness） |
| 实测结果 | **Files=2, Tests=1, Result: PASS**，失败 0 |
| 跳过项 | **1 个**：`99pod.t`（`Test::Pod 1.00 required for testing POD`）|
| 实际执行内容 | `t/00use.t`：`require Test::Future::IO::Impl` + `pass`（1 用例）|
| 覆盖边界 | 上游 t/ **不触发** 13 个验收套件——它们需调用方先加载 Future::IO 实现（本环境不可得）。属依赖链限制，未伪造通过率 |
| 是否入 build | **是**（`upstream_test_in_build: true`）|
| 上游测试改动 | **无**（原样运行）|

## 验证结果

```bash
# conan create（含 test_package R34 消费者验证）——rc=0
conan create archives/t/test-future-io-impl/0.21 -pr:h=... -pr:b=... --build=missing
test-future-io-impl/0.21: package(): Packaged 1 '.pm' file
...
ok 1 - Test::Future::IO::Impl version is 0.21
...（11 项断言）
OK: test-future-io-impl 0.21 python-driven consumer check
```

test_package 消费者测试覆盖（11 条，全过）：

- **自有断言 5 条**：版本号；`run_tests` 已导出；13 个验收套件 + `time_about`
  齐备；未知套件名必须 die
- **真实套件 6 条**（配 Future::IO 桩实现驱动 `run_tests 'sleep'`）：
  `sleep(0.2)` 时长正确；sleep 可被 cancel；`->await` 返回 Future；
  await 后 `$f2`/`$f1` 均就绪；`alarm(now+0.2)` 时长正确

## 注意事项

- 纯 Perl 包不涉及交叉编译工具链；`make` 使用宿主 perl 即可。
- 解释器固定 `/data/service/hnp/bin/perl`（5.42.0）：本模块 `use Errno qw(EAGAIN
  EINVAL EPIPE)` 且用 `Errno::ECONNREFUSED`，需规避设备 perl 5.42.2 的别名去重问题。
- 消费者脚本只实跑 `sleep` 套件（自包含，不需 socket/pipe/fork），以保证在
  容器/CI 中稳定复现；其余套件（accept/connect/poll/read/... 与 waitpid 的
  fork）需要真实实现与更宽松的环境，留给消费方按需运行。

## 对话记录

### 对话 #1（2026-09-18）

- 在鸿蒙 aarch64 设备上完成适配：`conan create` 通过。
- 上游测试真实运行：t/ 2 文件 1 用例通过（1 skip 为 Test::Pod 可选依赖）。
- 消费者测试 11/11 通过：既核验 13 个验收套件与计时助手齐备，又配 Future::IO
  桩实现真实跑通 sleep 套件。
- 零补丁：未改动上游源码，仅新增等价 Makefile.PL。
- 如实申报覆盖边界：13 个套件需 Future::IO 实现才能实跑，而该依赖链在本环境
  与 ohpcd 均不可得（仓内 future/0.52 尚在 PR 阶段），未以任何方式伪造通过率。
---

**编译结束**: 2026-09-18 05:29
**最终状态**: built
