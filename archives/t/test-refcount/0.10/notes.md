# test-refcount 0.10 适配笔记

## 编译环境
- **构建系统**: 纯 Perl（上游 Module::Build → 适配为 ExtUtils::MakeMaker）
- **编译日期**: 2026-09-18
- **平台**: arm64-ohos（OpenHarmony PC），perl 5.42.0（/data/service/hnp）
- **状态**: built（Conan 配方验证通过）
- **补丁数量**: 0（不改动上游源码；Makefile.PL 为新增构建脚本）

## 软件简介

Test::Refcount 提供断言 Perl 变量**引用计数**的测试辅助函数，用于检查类/函数
是否泄漏引用（DESTROY 时机的关键）。单模块 `lib/Test/Refcount.pm`，无 XS。

| 函数 | 导出 | 说明 |
|------|------|------|
| `is_refcount( $obj, $count, $name )` | `@EXPORT` | 断言 `$obj` 有 `$count` 个引用 |
| `is_oneref( $obj, $name )` | `@EXPORT` | 断言 `$obj` 只有 1 个引用 |
| `refcount( $obj )` | `@EXPORT_OK` | 返回引用数（0.09 新增）|

失败时给出诊断（`expected N references, found M`），并在装了可选增强
`Devel::MAT` / `Devel::FindRef` 时附堆转储/引用链。

## 编译步骤（conan create 全流程）

```bash
conan create archives/t/test-refcount/0.10 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

### 1. 源码获取（source()）
`get()` 从 conandata 声明的 CPAN 官方发行下载并 strip_root
（目录 Test-Refcount-0.10）。

### 2. 构建（build()）——核心适配点

上游构建系统是 **Module::Build**（`Build.PL`，configure_requires
`Module::Build >= 0.4004`），OHOS 不可得（设备 perl 与 hnp perl 均无
`Module/Build.pm`；制品仓 `conan search perl-module-build/*` 为 0 个）。

对策：**用 perl 核心 ExtUtils::MakeMaker 生成等价 Makefile.PL**，逐项转写
上游 Build.PL 的 `module_name` / `requires` / `test_requires`。上游另有两项
**未**写入 PREREQ_PM，理由如下：

| 上游声明 | 处理 | 理由 |
|---|---|---|
| `recommends => { 'Devel::MAT' => '0.04' }` | 不写入 | 可选增强；缺失时模块以 `HAVE_DEVEL_MAT_DUMPER=0` 降级，上游测试亦按该常量分支。写入会把可选依赖变成硬依赖 |
| `extra_manify_args => { utf8 => 1 }` | 不写入 | 仅影响 manpage 生成，非构建必需 |

随后 `perl Makefile.PL INSTALLDIRS=site` → `make` → `make test` →
`make install DESTDIR=<staging>`。

### 3. 打包（package()）
- 按登台树原样拷入 package_folder
- 以遍历定位 `Test/Refcount.pm` 后**回溯父级**得到 site 目录（安装前缀随
  perl 构建而异；沿用 metrics-any 0.10 的教训，避免返回 `Test/` 本身）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者脚本 `use Test::Refcount qw( refcount );` 编译期报 `plan() doesn't understand refcount` | `Test::Refcount` 继承 `Test::Builder::Module`，其 `import` 把**位置参数当 plan 参数**，不认 `qw( refcount )` | 按上游 POD 写法改用 `use Test::Refcount import => [qw( is_refcount is_oneref refcount )]` |
| 2 | 去掉参数后运行期报 `Undefined subroutine &main::refcount` | 只写 `use Test::Refcount;` 仅导入 `@EXPORT`（`is_refcount`/`is_oneref`），`refcount` 在 `@EXPORT_OK`，不会自动进入调用者命名空间 | 同 #1，用 `import => [...]` 显式取 `@EXPORT_OK` |
| 3 | 断言「各引用类型 refcount 均为 1」失败 | `my $var; my $ref = \$var;` 让标量同时被**词法槽位**与引用持有（实测 refcount=2）；正则引用在现代 perl 起始 refcount 即为 2 | 按上游写法 `do { my $var; \$var }` 让槽位及时出作用域；不纳入 Regex 类型（上游 `t/04reftypes.t` 对该类型显式 skip）|
| 4 | 负向（失败路径）脚本的断言诊断文案在 **stderr**，驱动只读 stdout 导致校验失败 | Test::Builder 把 `#   ...` 诊断写 stderr，TAP 结果行写 stdout | 驱动同时读取两流并合并校验 |

## 依赖

| 类型 | 依赖 | 状态 |
|---|---|---|
| runtime | B / Scalar::Util / Test::Builder | 均为 perl 核心模块，OHOS perl 内建 ✅ |
| runtime（可选）| Devel::MAT >= 0.04 | 上游 `recommends`，**故意不纳入**（可选增强）✅ |
| configure | Module::Build >= 0.4004 | **OHOS 不可得** → MakeMaker 替代 ✅ |
| test | Test::Builder::Tester / Test::More >= 0.88 | OHOS perl 自带 ✅ |
| Conan | 无 | — |

## 上游测试（R51 申报表）

| 项 | 内容 |
|---|---|
| 测试清点 | `t/` 目录 **6 个 .t 文件** |
| 运行方式 | `make test`（MakeMaker 的 test 目标驱动 TAP::Harness） |
| 实测结果 | **Files=6, Tests=20, Result: PASS**，失败 0 |
| 跳过项 | **1 个**：`99pod.t`（`Test::Pod 1.00 required for testing POD`）|
| 测试手法 | 上游用 `Test::Builder::Tester` 捕获被测断言产生的 TAP 并比对期望 —— 同时覆盖成功与失败两条路径 |
| 是否入 build | **是**（`upstream_test_in_build: true`）|
| 上游测试改动 | **无**（原样运行）|

## 验证结果

```bash
# conan create（含 test_package R34 消费者验证）——rc=0
conan create archives/t/test-refcount/0.10 -pr:h=... -pr:b=... --build=missing
test-refcount/0.10: package(): Packaged 1 '.pm' file
...
ok 1 - Test::Refcount version is 0.10
...（正向 12 条 + 失败路径 4 条）
OK: test-refcount 0.10 python-driven consumer check
```

test_package 消费者测试覆盖（16 条）：

- **正向（12 条，要求全过）**：版本号；`is_oneref`/`is_refcount`；别名后引用数
  上升、`undef` 后回落；`refcount()` 公开 API；**weak 引用不计入**；**循环自引用
  计为 2**；SCALAR/ARRAY/HASH/CODE/GLOB 各类型；导出接口齐全
- **失败路径（4 条，故意失败）**：非引用入参须报 `expected a reference, was not
  given one`；引用数不符须报 `expected 1 references, found 2` —— 由 .py 驱动核对
  真实诊断文案，因此「故意失败」本身是被验证的行为

## 注意事项

- 纯 Perl 包不涉及交叉编译工具链；`make` 使用宿主 perl 即可（OHOS 上即目标平台原生）。
- 解释器固定 `/data/service/hnp/bin/perl`（5.42.0），与 metrics-any 0.10 口径一致。
- 消费者的失败路径断言**必须独立进程**运行（本次由 `.py` 驱动拆两个脚本），
  否则故意失败的断言会污染正向脚本的 TAP 计划。

## 对话记录

### 对话 #1（2026-09-18）

- 在鸿蒙 aarch64 设备上完成适配：`conan create` 通过。
- 上游测试真实运行：t/ 6 文件 20 用例全过（1 skip 为 Test::Pod 可选依赖）。
- 消费者测试 16 条（正向 12 + 故意失败 4）通过。
- 零补丁：未改动上游源码，仅新增等价 Makefile.PL。
- 本次四处实测教训已记入 knowledge_gained 与知识草稿
  `DRAFT-test-refcount-import-and-refcount-semantics`：①Test::Builder::Module 子类
  取 `@EXPORT_OK` 须用 `import => []`；②匿名标量引用要用 `do{}` 隔离槽位；
  ③Regex 引用起始 refcount 为 2（上游已 skip）；④诊断文案在 stderr。
---

**编译结束**: 2026-09-18 04:44
**最终状态**: built
