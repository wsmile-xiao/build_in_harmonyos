# DRAFT-perl-module-build-makemaker-substitution — CPAN 发行版以 Module::Build（Build.PL）为构建系统而 OHOS 缺该模块时，用 ExtUtils::MakeMaker 生成等价 Makefile.PL 继续构建

## 错误特征

```
Can't locate Module/Build.pm in @INC (you may need to install the Module::Build module)
 (@INC entries checked: .../site_perl/5.42.2 .../lib/5.42.2)
BEGIN failed--compilation aborted.
```

同族变体（Module::Build::Tiny 构建的发行版）：

```
Can't locate Module/Build/Tiny.pm in @INC
```

触发点：`perl Build.PL` 首步即失败，`./Build` 不存在，构建无法推进。

## 触发条件

- 构建系统: CPAN 发行版的 Module::Build（`Build.PL`）/ Module::Build::Tiny
- 阶段: configuration（`perl Build.PL` 第一步）
- 环境: OHOS 只带 perl 核心模块，无 Module::Build

## 根因分析

上游发行版的 `Build.PL` 把 Module::Build 声明为**构建期**依赖
（`configure_requires => { 'Module::Build' => '>= 0.4004' }`）。OHOS 环境里：

1. 设备 perl 5.42.2 无 `Module/Build.pm`；
2. OHOS 预装 perl 5.42.0（`/data/service/hnp/bin/perl`）同样没有；
3. 制品仓也无 `perl-module-build` 制品。

因此 `perl Build.PL` 无法执行。

**判定陷阱（重要）**：用 `conan download <pkg> -r=ohpcd` 探测不存在的包时，报的是
误导性的 `ERROR: error:system acceleration policy not enabled` —— 与网络/权限故障
不可区分。判定制品存在性必须用 `conan search <pkg>/* -r=ohpcd`：

```
$ conan search "perl-module-build/*" -r=ohpcd
Found 0 pkg/version recipes matching perl-module-build/* in ohpcd
```

对照已知存在的包（`conan search perl-exporter/*` → `Found 1 pkg/version recipes`）。

## Recommended Solution

### 主方案（priority 1）— `build-script-substitution`

在 conanfile.py 的 `build()` 中，源码根目录没有 `Makefile.PL` 时生成一个，
**逐项转写**上游 Build.PL 的 `module_name` / `requires` / `test_requires`
（与 META.json 的 `prereqs` 对齐，避免遗漏运行时依赖声明）：

```python
MAKEFILE_PL = """\
use strict; use warnings; use ExtUtils::MakeMaker;
WriteMakefile(
    NAME             => 'Future',
    VERSION_FROM     => 'lib/Future.pm',
    LICENSE          => 'perl_5',
    MIN_PERL_VERSION => '5.014',
    PREREQ_PM        => { 'Carp'=>'1.25', 'List::Util'=>'1.29',
                          'Test::Builder::Module'=>0, 'Time::HiRes'=>0,
                          'perl'=>'5.014' },
    TEST_REQUIRES    => { 'Test2::V0' => '0.000148' },
    NO_MYMETA        => 1,
);"""

def build(self):
    if not os.path.exists(os.path.join(self.source_folder, "Makefile.PL")):
        ...  # 写入等价的 Makefile.PL
    self.run(f"{perl} Makefile.PL INSTALLDIRS=site", cwd=self.source_folder)
    self.run("make", cwd=self.source_folder)
    self.run("make test", cwd=self.source_folder)     # R51 上游测试真实运行
    self.run(f'make install DESTDIR="{staging}"', cwd=self.source_folder)
```

**仅新增构建脚本、不改动上游源码，因此无需补丁（`patches: {}`）。**

纯 Perl 模块的打包要点：

| 项 | 做法 | 原因 |
|---|---|---|
| package_type | `python-require` | 无 C/C++ 二进制产物；无 bindirs → 无需 commands.json（R38 不适用） |
| 定位站点目录 | 遍历找 `Future.pm` | `make install DESTDIR=` 的安装前缀**随 perl 构建而异**（如 `/data/service/hnp/perl.org/perl_5.42.0/lib/site_perl/5.42.0`），不可硬编码 |
| 消费者可用性 | `runenv_info.define_path("PERL5LIB", site)` | 下游 perl 脚本可直接 `use Future` |
| 上游测试 | `make test` 纳入 build() | R51：上游 t/ 套件真实运行并回填通过率 |

### 回退方案（priority 2）— `tool-requires-module-build`

若上游 `Build.PL` 含必须由 Module::Build 执行的逻辑（自定义 Action、
`auto_configure_requires` 等），先立项把 Module::Build 适配并发布为
`tool_requires`（perl-module-build），再走原生 `perl Build.PL → ./Build`。

注意 E137：OHOS perl 的 `ldflags`/`lddlflags` 含 `-fstack-protector-strong`，
会使 `ExtUtils::CBuilder` 的编译器探测失败（ld.lld 不识别该编译期选项）——
XS 场景需先按 E137 处理。

### 禁止做法

- ❌ 删除 / 改写上游 `Build.PL`（破坏上游源码，不可复现、不可上游）
- ❌ 跳过 `make test` 让构建"变绿"（R51：上游测试是强制申报内容，跳过即以掩盖换通过）
- ❌ 用 `conan download` 的报错判断制品是否存在（语义误导，必须用 `conan search`）

## 单库实证（2026-09-18）

| 库 | 处理 | 结果 |
|---|---|---|
| future 0.52（CPAN Future，纯 Perl） | 生成等价 Makefile.PL（转写 Build.PL 的 requires/test_requires）；`make test` 纳入 build() | **Files=56, Tests=778, Result: PASS**（24 个 skip 文件均为可选依赖缺失——22 个 `-xs` 变体需 Future::XS、52awaitable-future-pp.t 需 Awaitable、99pod.t 需 Test::Pod，零失败）；消费者测试 16/16 通过；零补丁 |

同策略先例：**perl-parallel-pipes 0.201**（上游 Module::Build::Tiny 同样在 CI worker 缺失，
配方同样生成 Makefile.PL 走 ExtUtils::MakeMaker）。

## 测试覆盖边界

- 本条解决的是**构建入口缺失**与**依赖存在性判定口径**两个问题；
  若 Module::Build 自身被立项适配并发布（回退方案落地），主方案不再是唯一路径。
- XS 类发行版还叠加 E137（`-fstack-protector-strong` 进 lddlflags → CBuilder 探测失败），
  本条不覆盖该问题的修复，仅在回退方案中提示。
- 上游测试通过率随 perl 版本与可选测试依赖（Test2::V0/Test::Pod）安装情况变化，
  申报时须注明实测环境。

## 关联条目

- 相似：`E137`（OHOS perl ldflags 含 -fstack-protector-strong → ExtUtils::CBuilder 探测失败）、`E155`
- 相关：`DRAFT-ohos-legacy-pytest-collector`（同属"上游测试怎么真跑"这一类）
