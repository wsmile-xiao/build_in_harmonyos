# future 0.52 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（上游 Module::Build → 适配为 ExtUtils::MakeMaker）
- **编译日期**: 2026-09-18
- **平台**: arm64-ohos（OpenHarmony PC），perl 5.42.0/5.42.2
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（不改动上游源码；Makefile.PL 为新增构建脚本）

## 软件简介

Future 提供"等待完成的异步操作"抽象（promise/future 模式），是 Perl
异步生态的基础模块：`done/fail/then/else/wait_all/needs_all` 组合器，
`Future::Utils`（call/repeat/fmap_*）、`Future::Mutex`（临界区串行化）、
`Future::Exception`、`Test::Future` 测试辅助。纯 Perl，无 XS。

## 编译步骤（conan create 全流程）

```bash
python3 scripts/ohc-run.py conan create archives/f/future/0.52 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Future-0.52）。

### 2. 构建（build()）——核心适配点

上游构建系统是 **Module::Build**（`Build.PL`，configure_requires
`Module::Build >= 0.4004`），但 Module::Build 在 OHOS 环境不可得：

- 设备 perl 5.42.2（`/storage/Users/currentUser/usr/local/bin/perl`）：
  `Can't locate Module/Build.pm in @INC`
- OHOS 预装 perl 5.42.0（`/data/service/hnp/bin/perl`）：同上
- 制品仓：`conan search perl-module-build/* -r=ohpcd` → **0 个**
  （注意：`conan download` 对不存在/未发布的包报的是误导性的
  `system acceleration policy not enabled`，无法据此判断存在性，
  必须用 `conan search` 或 `conan list`）

对策（先例：perl-parallel-pipes 0.201，同样以 MakeMaker 替代上游缺失的
Module::Build::Tiny）：**用 perl 核心模块 ExtUtils::MakeMaker 生成等价的
Makefile.PL**，逐项转写上游 Build.PL 的 `module_name` / `requires` /
`test_requires`，因此运行时依赖声明与 META.json 的 prereqs 保持一致。

```perl
WriteMakefile(
    NAME             => 'Future',
    VERSION_FROM     => 'lib/Future.pm',
    LICENSE          => 'perl_5',
    MIN_PERL_VERSION => '5.014',
    PREREQ_PM        => { Carp=>'1.25', List::Util=>'1.29',
                          'Test::Builder::Module'=>0, Time::HiRes=>0,
                          perl=>'5.014' },
    TEST_REQUIRES    => { 'Test2::V0' => '0.000148' },
    NO_MYMETA        => 1,
);
```

随后 `perl Makefile.PL INSTALLDIRS=site` → `make` → `make test` →
`make install DESTDIR=<staging>`。

### 3. 打包（package()）
- 按登台树原样拷入 package_folder（保留 make install 的 site 布局）
- 以遍历定位 `Future.pm` 确认打包成功——**安装前缀随 perl 构建而异**
  （实测 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0`），
  不可硬编码路径
- package_type=**python-require**（纯 Perl 模块无二进制产物，沿用
  perl-uri 5.35 / perl-io-multiplex 1.16 先例）→ 无 bindirs → 无需
  commands.json（R38 仅约束构建可执行文件的包）
- `package_info()` 以 `runenv_info.define_path("PERL5LIB", site)` 注入，
  下游 perl 脚本可直接 `use Future`；`cpp_info.libs = []`（R26 不适用）

## 依赖

| 类型 | 依赖 | 状态 |
|---|---|---|
| runtime | Carp>=1.25 / List::Util>=1.29 / Test::Builder::Module / Time::HiRes / perl>=5.014 | 全为 perl 核心模块，OHOS perl 内建 ✅ |
| configure | Module::Build>=0.4004 | **OHOS 不可得** → MakeMaker 替代 ✅ |
| test | Test2::V0>=0.000148 | OHOS perl 自带（实测 v1.302210）✅ |
| Conan | 无 | — |

## 上游测试（R51 申报表）

| 项 | 内容 |
|---|---|
| 测试清点 | `t/` 目录 **56 个 .t 文件**（ls t/*.t \| wc -l）；另有 22 个同名 `.pl` 为主驱动脚本 |
| 运行方式 | `make test`（MakeMaker 的 test 目标驱动 TAP::Harness） |
| 实测结果 | **Files=56, Tests=778, Result: PASS**，失败 0 |
| 跳过项 | **24 个文件跳过**，均为可选变体非失败：22 个 `*-xs` 变体（需 `Future::XS`，本发行版不含 XS 实现，源码 `lib/Future/PP.pm` 即纯 Perl 实现）、`52awaitable-future-pp.t`（需 `Test::Future::AsyncAwait::Awaitable`）、`99pod.t`（需 `Test::Pod` 1.00） |
| 是否入 build | **是**（`upstream_test_in_build: true`）——conan create 内真实执行 make test |
| 上游测试改动 | **无**（原样运行，不改测试代码） |

日志留存：`.tmp/future-r51/make-test.log`（临时产物，不入库）。

## 与上游 API 的核对（写 test_package 时的实测结论）

下列语义按上游 `t/` 实测确认，首次撰写 consumer 测试时曾写错：

- `Future->wait_all(...)` 的 `result` 返回**各子 future 本身**（不是它们的返回值）；
  要拿返回值用 `needs_all`。
- `Future::Utils::call { }` 的 code 块**必须返回 Future**；返回非 future 会被
  转为立即失败（`die` 同样转为立即失败）。
- `Future::Utils::fmap_void { }` 的 code 块**必须返回 Future**，且整体
  `result` 是空列表。
- `Future::Mutex->enter(\&code)` 的 code 块**必须返回 Future**。

## 验证结果

```bash
# conan create（含 test_package R34 消费者验证）——rc=0
conan create archives/f/future/0.52 -pr:h=... -pr:b=... --build=missing
future/0.52: package(): Packaged 7 '.pm' files
future/0.52: Created package revision 50f89208d0de3905136b348c9ce544cb
...
ok - Future version is 0.52
...（16 项断言）
ALL OK
OK: future 0.52 python-driven consumer check
```

test_package 消费者测试覆盖（16 项断言，全过）：版本号、`done/get/is_ready`、
`then` 链式、`fail/failure`、`wait_all`、`needs_all`、`Future::Utils::call`
（正常返回 + die 转失败）、`fmap_void`（遍历 + 空结果）、`repeat`、
`Future::Mutex`（available + 临界区串行化）、`Future::Exception` 打包与加载，
并校验 6 个模块文件（Future.pm、Future/PP.pm、Utils.pm、Mutex.pm、
Exception.pm、Test/Future.pm）均在打包目录内。

## 注意事项

- Build.PL 的 `x_breaks` 检查（对已装 IO::Async 等模块做版本告警）在
  MakeMaker 路径下不生效——本环境无这些模块，且该逻辑仅作用于已装
  旧版依赖的终端用户，不影响本包构建与功能。
- Makefile.PL 的 `ABSTRACT_FROM` 会告警 `Setting ABSTRACT via file
  'lib/Future.pm' failed`（上游 pod 的 ABSTRACT 抽取格式不被 EUMM 识别），
  无害且不影响构建产物。
- 纯 Perl 包不涉及交叉编译工具链，`make` 使用宿主机 perl/make 即可
  （OHOS 上即目标平台原生）。

## 对话记录

### 对话 #1（2026-09-18）

- 在鸿蒙 aarch64 设备上完成适配：`conan create`（G1/G2/G3/G4 + L2/L4/L5 全过），
  W3 本地 CI 模拟通过（L0/L1/L4/L5 pass，L2 skip：纯库无 bin/）。
- 上游测试套件真实运行：t/ 56 个 .t 文件，`make test` 实测 **Files=56, Tests=778,
  Result: PASS**，零失败（24 个 skip 文件均为可选依赖缺失，非失败：22 个 `*-xs.t`
  变体需 Future::XS、52awaitable-future-pp.t 需 Awaitable、99pod.t 需 Test::Pod）。
  测试已纳入 build()，
  非事后补跑。
- 消费者测试（R34）16/16 通过，覆盖 Future 核心与 Utils/Mutex/Exception。
- 零补丁：未改动任何上游源码，仅在 build() 中新增等价 Makefile.PL
  （替代 OHOS 不可得的 Module::Build）。
- 期间核验并纠正了两处判定：①Module::Build 的存在性判定须用 `conan search`
  （`conan download` 报的 "system acceleration policy not enabled" 语义误导）；
  ②上游 Test2::V0 版本要求由 OHOS perl 自带（v1.302210）满足，故上游测试可真跑。
---

**编译结束**: 2026-09-18 03:25
**最终状态**: built
