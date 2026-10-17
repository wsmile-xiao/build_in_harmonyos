# test-future-io-impl

[Test::Future::IO::Impl](https://metacpan.org/pod/Test::Future::IO::Impl) —
**Future::IO 实现方的验收测试工具集**（Perl）。

## 简介

`Future::IO` 提供异步 I/O 抽象，第三方可以写自己的实现
（`Future::IO::Impl::*`）。本模块把「实现必须满足的行为规范」固化成一套
验收测试：实现方的测试脚本只需一行 `run_tests 'sleep'`，即可验证自己的
实现是否符合契约。

```perl
# 实现方（Future::IO::Impl::MyNewImpl）的 t/ 脚本
use Test::More;
use Test::Future::IO::Impl;

use Future::IO;
use Future::IO::Impl::MyNewImpl;    # ← 必须先加载被测实现

run_tests 'sleep';                  # 跑某个套件（可传多个）
done_testing;
```

| 符号 | 导出方式 | 说明 |
|------|---------|------|
| `run_tests @suitenames` | `@EXPORT` | 按名分发执行验收套件；未知套件名 `die` |
| `time_about(&\@)` | — | 计时断言助手（窗口 0.9×~1.5×），套件内部使用 |

**13 个验收套件**：

| 套件 | 验收目标 |
|------|---------|
| `accept` / `connect` | socket 接受/连接 |
| `poll` / `poll_no_hup` | `poll` 的 POLLIN/POLLOUT/POLLHUP 语义 |
| `read` / `sysread` | 等价读方法（0.17 重命名前后两个名）|
| `recv` / `recvfrom` | 数据报接收 |
| `send` | 数据报发送 |
| `sleep` | `sleep` / `alarm` 计时与取消、`->await` 语义 |
| `write` / `syswrite` | 等价写方法 |
| `waitpid` | 子进程回收（含 fork）|

## OHOS 适配

- **纯 Perl 模块**：无 XS、无 C/C++ 编译、无平台相关代码；运行时依赖
  `Errno` / `IO::Handle` / `Socket` / `IO::Poll` / `Time::HiRes` / `Test2::V0`
  在 OHOS perl 中齐备。
- **构建系统替换**：上游以 `Module::Build`（`Build.PL`）为构建系统，而 OHOS
  环境不带该模块（设备 perl 5.42.2 与 `/data/service/hnp/bin/perl` 5.42.0 均无
  `Module/Build.pm`，制品仓也无 `perl-module-build` 制品）。配方在 `build()` 中
  用 perl 核心模块 `ExtUtils::MakeMaker` 生成**等价 Makefile.PL**。
- **零补丁**：仅新增构建脚本，未改动任何上游源码，故 `patches: {}`。
- **打包**：`package_type = "python-require"`（纯 Perl 无二进制产物，无 bindirs
  → 无需 `commands.json`）。模块位于 `<site>/Test/Future/IO/Impl.pm`（三层），
  site 根需**逐级上溯三层**；`package_info()` 注入 `PERL5LIB`。

> ⚠️ **依赖链与覆盖边界（如实说明）**：本模块的 `run_tests` 要求调用方先加载一个
> **`Future::IO` 实现**才能运行 13 个套件。而 `Future::IO` 在本环境与 ohpcd
> 制品仓均不存在，本仓 main 亦无相应归档（依赖链 `Future::IO` → `Future`，仓内
> `future/0.52` 尚处 PR 阶段）。因此：
> - 上游 `t/` 只覆盖模块加载（`00use.t`，1 用例）；
> - test_package 侧由一份 **Future::IO 桩实现**真实驱动自包含的 `sleep` 套件
>   （6 项断言），并核验 13 个套件与 `time_about` 齐备；
> - 其余套件（socket/fork 类）待 `Future::IO` 及某个实现在本环境适配后，由其
>   消费方运行。**本包作为工具的构建与安装不受影响**。

## 依赖

运行时（META）：`Errno` / `IO::Handle` / `Socket` / `Time::HiRes` / `Test2::V0`
（perl 核心或环境已有）；构建：`ExtUtils::MakeMaker`（perl 核心）。
无 Conan 依赖。逻辑依赖：`Future::IO` + 一个实现（见上）。

## 功能验证

```bash
# 上游测试套件（2 文件，实际执行 00use.t）
cd Test-Future-IO-Impl-0.21 && perl Makefile.PL INSTALLDIRS=site && make && make test
# → Files=2, Tests=1, Result: PASS（99pod.t skip：需 Test::Pod）

# 消费者验证（conan create 内 test_package，11 条断言）
conan create archives/t/test-future-io-impl/0.21 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

## 参考

- 文档: https://metacpan.org/pod/Test::Future::IO::Impl
- 发行版: https://metacpan.org/dist/Test-Future-IO-Impl
- 源码: https://cpan.metacpan.org/authors/id/P/PE/PEVANS/Test-Future-IO-Impl-0.21.tar.gz
