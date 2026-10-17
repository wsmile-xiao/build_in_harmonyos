# class-inspector 1.36 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（上游自带 Makefile.PL，由 Dist::Zilla 生成）
- **编译日期**: 2026-09-18
- **平台**: arm64-ohos（OpenHarmony PC），perl 5.42.0（/data/service/hnp）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（未改动上游任何文件）

## 版本选择说明

按任务提供的源码 URL 取 **1.36**：
`https://cpan.metacpan.org/authors/id/P/PL/PLICEASE/Class-Inspector-1.36.tar.gz`（官方 CPAN 可得）。

- 本目录曾按「任务版本号 1.3 的字面截断」误取 **1.30**，经用户以源码 URL 纠正；
  1.30 归档与对应 PR 已撤下，本版本为唯一交付。
- 1.36 同时是本仓既有 consumer `perl-pod-spell/1.27` 依赖列表所锚定的版本。

## 软件简介

Class::Inspector 提供「友好地获取已加载类的信息」：

| 方法 | 说明 |
|------|------|
| `installed( $class )` | 类是否已安装且在 @INC 内可解析 |
| `loaded( $class )` | 类是否已加载（查符号表）|
| `filename( $class )` | 类的 @INC **相对**路径（如 `Class/Inspector.pm`）|
| `resolved_filename( $class )` | 走 @INC 解析出的**真实**文件路径 |
| `loaded_filename( $class )` | 类**实际加载自**的路径 |
| `functions( $class )` | 类内全部函数名列表 |
| `function_refs( $class )` | 类内全部函数的 CODE 引用 |
| `function_exists( $class, $f )` | 某函数是否存在 |
| `methods( $class, $type, $vis )` | 方法列表（可按 public/private 过滤）|
| `subclasses( $class )` | 已加载的子类列表（**三态返回**，见下）|

另有函数式接口 `Class::Inspector::Functions`（`@EXPORT` 6 个 + `@EXPORT_OK` 4 个）。

## 编译步骤（conan create 全流程）

```bash
conan create archives/c/class-inspector/1.36 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Class-Inspector-1.36）。

### 2. 构建（build()）

上游**自带 Makefile.PL**，由 `Dist::Zilla::Plugin::Author::Plicease::MakeMaker
v2.37` 生成，直接 `use ExtUtils::MakeMaker`。关键点：**发行版内不含 `inc/`**
（不是 Module::Install，也不是 Module::Build），因此：

```
perl Makefile.PL INSTALLDIRS=site → make → make test → make install DESTDIR=<staging>
```

**开箱可用，无需生成替代构建脚本**。各版本构建系统差异对照：

| 版本 | 构建系统 | 本配方做法 |
|---|---|---|
| class-inspector **1.36** | Dist::Zilla → 普通 Makefile.PL（ExtUtils::MakeMaker），**无 inc/** | **沿用上游** |
| class-inspector 1.30（已撤下）| Module::Install（引导随包在 `inc/`，8 个文件）| 沿用上游 |
| future / metrics-any / test-refcount / test-future-io-impl | Module::Build（仅 `Build.PL`）| 生成等价 Makefile.PL |

> 同一软件的两个版本构建系统就不同——**必须逐包（逐版本）实地确认**，不能类推。

### 3. 打包（package()）
- 按登台树原样拷入 package_folder
- 以遍历定位 `Class/Inspector.pm` 后**上溯一级**得到 site 目录

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者断言 `->subclasses returns an ARRAY ref` 失败 | `subclasses()` 有**三态**返回值：命中→ARRAY ref、无命中→**空字符串 `''`**、类名非法→**undef**（实现 `@found ? \@found : ''`，非法类名经 `_class` 守卫返回 undef）| 按上游 `t/class_inspector.t` 的写法分三态断言；并定义 `Class::Inspector::Dummy` 子类覆盖命中场景 |
| 2 | 传非法类名给 `installed()` 触发上游警告 `Use of uninitialized value $filename` | 非法类名让上游 `_inc_filename` 拿到 undef | 类名校验改用上游的 `_class()`（其校验契约）|
| 3 | 驱动里的 TAP 计划写成 `1..31` 与实测不符 | 我按断言条数**估算**而非实测 | 实测为 `1..30`，已按实测修正（断言数一经写入测试即由测试自身强制）|
| 4 | 曾误取版本 1.30 | 按任务版本号「1.3」的字面截断猜测 | 以用户提供的**源码 URL** 为准改建 1.36 |

## 依赖

| 类型 | 依赖 | 状态 |
|---|---|---|
| runtime | File::Spec >= 0.80 / base | perl 核心模块 ✅ |
| configure | ExtUtils::MakeMaker / perl >= 5.008 | perl 核心 ✅ |
| test | Test::More >= 0.98 | perl 核心 ✅ |
| develop（不参与 make test）| Test::EOL / Test2::Tools::PerlCritic / Test::Pod::Spelling::CommonMistakes 等 | 作者侧 `xt/` 测试用，本适配不涉及 ⚪ |
| Conan | 无 | — |

## 上游测试（R51 申报表）

| 项 | 内容 |
|---|---|
| 测试清点 | `t/` 目录 **6 个 .t 文件** |
| 运行方式 | `make test`（MakeMaker 的 test 目标驱动 TAP::Harness） |
| 实测结果 | **Files=6, Tests=86, Result: PASS**，失败 0；执行口径 **85 通过 + 1 个 skip 用例** |
| 跳过项 | **1 个用例** + **1 个文件**：①`t/class_inspector__inc_to_local.t` 内 `skip( "Skipping Win32 test", 1 ) unless $^O eq 'MSWin32'`（本机 Linux 故触发，输出 `ok 1 # skip Skipping Win32 test`）；②文件级 `t/class_inspector__devel_hide.t`（`skipped: test requires Devel::Hide`，可选测试依赖缺失）。两者均非失败 |
| 分文件用例数（逐文件 TAP 计划实测）| `00_diag.t` **1** + `01_use.t` 3 + `class_inspector.t` 56 + `class_inspector__inc_to_local.t` 2 + `class_inspector_functions.t` 24 = **86 已执行**；`devel_hide` 为 `plan skip_all`（声明 tests=>2，实际 0）。⚠️ 不可按 diag 行数估算（`00_diag.t` 虽打印 4 行模块版本 diag，用例只有 1 个）|
| 是否入 build | **是**（`upstream_test_in_build: true`）|
| 上游测试改动 | **无**（原样运行）|

## 验证结果

```bash
# conan create（含 test_package R34 消费者验证）——rc=0
conan create archives/c/class-inspector/1.36 -pr:h=... -pr:b=... --build=missing
...
ok 1 - Class::Inspector version is 1.36
...（30 项断言）
1..30
OK: class-inspector 1.36 python-driven consumer check
```

test_package 消费者测试覆盖（30 条，全过）：

- **版本与加载态**：版本号；`loaded`/`installed` 正反例
- **路径类**：`filename`（@INC 相对名）、`loaded_filename`、`resolved_filename`
  （且解析出的文件真实存在）
- **函数类**：`functions`（含私有 `_class`）、`function_refs`（CODE 引用）、
  `function_exists` 正反例
- **方法类**：`methods` 返回数组且含公开方法
- **子类类**：`subclasses` 三态（命中 ARRAY ref / 无命中 `''` / 非法 undef）
- **校验契约**：`_class` 对合法、格式合法未安装、长类名、缺失、数字开头、
  非法字符六类输入的判定
- **函数式接口**：`Class::Inspector::Functions` 10 个导出函数齐备、默认导出
  可导入、函数式 `installed()`/`loaded()` 可调用

## 注意事项

- 纯 Perl 包不涉及交叉编译工具链；`make` 使用宿主 perl 即可。
- 解释器固定 `/data/service/hnp/bin/perl`（5.42.0），与同批次 perl 包口径一致。
- **构建系统逐版本不同**：1.36 是普通 MakeMaker（无 `inc/`），1.30 是
  Module::Install（`inc/` 随包）——不要把一个版本的做法套到另一个版本上。
- 本仓 consumer `perl-pod-spell/1.27` 依赖列表中记的是 `perl-class-inspector/1.36`
  （带 `perl-` 前缀、版本一致）；本 PR 按任务下发的包名 `class-inspector` 落档，
  两者包名风格不同但版本一致，可并存。

## 对话记录

### 对话 #1（2026-09-18）

- 初次按任务版本号「1.3」的字面截断误取 1.30 并提交 PR #10706。
- 用户以源码 URL（`.../PLICEASE/Class-Inspector-1.36.tar.gz`）纠正：1.36 确实存在。
- 遂改建 `feat/class-inspector-1.36`：重新侦察（6 文件 86 用例、无 `inc/`、
  Dist::Zilla 生成的普通 Makefile.PL）、写配方与消费者测试、conan create 通过
  （30/30）、关闭旧 PR 并提交新 PR。
- 零补丁：上游自带 Makefile.PL，未改动任何上游文件。
- 教训：**版本的权威信号是源码 URL / 平台下发的制品名，不是版本号的字面截断猜测**。
---

**编译结束**: 2026-09-18 13:40
**最终状态**: built
