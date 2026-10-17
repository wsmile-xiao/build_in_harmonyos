# DRAFT-ohos-perl-pl-template-needs-manual-materialisation — Perl `.PL` **生成器**须运行它才能实例化

> Contributor: 6E19 / Status: **DRAFT** / Updated: 2026-09-17 / Severity: 2 (medium)
> Prospect ID: `DRAFT-ohos-perl-pl-template-needs-manual-materialisation`（正式编号由主编 `graph promote` 分配）

## 相关既有条目（同族差异化定位）

| 既有条目 | 收录状态 | 问题面 | 本条的增量（差异化） |
|---|---|---|---|
| `perl-carp` 等纯模块 Perl 包 | 已在 main | package_type=application + 拷 `lib/` → `lib/perl5` | 那类**只有 `lib/`**，不涉及脚本生成；**本条适用于含 `.PL` 生成器 / 可执行脚本的发行版** |
| `E155` / `E173` / `E208`（含 MakeMaker 语境）| 图谱 | Perl 构建相关（MakeMaker 使用）| 实测均非"`.PL` 生成器未被执行致交付物根本不是该工具"这一机制 |

**全库查证**：`PL_FILES`、`.PL 模板`、`podselect` 等关键词**命中 0**
（`MakeMaker` 有 7 处，`podselect` 仅本轮新增）。

## Scope（何时用）

**含 `.PL` 生成器脚本**（或被 MakeMaker 生成的其它构建期产物）的 Perl 发行版适配。

对照实测样本：**perl-pod-parser (Pod-Parser) 1.67** —— `scripts/podselect.PL`（3730 B）。

## Symptom

两种表现，取决于配方的处理方式：

| 配方做法 | 表现 |
|---|---|
| 只拷 `lib/` | 脚本**整个丢失**，`bin/` 为空 → 消费方调用即 `command not found` |
| 把 `.PL`「改首行」后当产物交付 | 交付的其实是**生成器本体**（文件里仍含 `print OUT` 代码），不是该工具；且生成器首行的 `#!/usr/local/bin/perl` 在 OHOS/CI **不存在** |

> 关键：症状出现在**运行期**（消费方执行脚本时），而非打包期——打包"看起来成功"，
> 脚本文件也确实"存在"。

## Root Cause

### `.PL` 不是"替换首行即得产物"的模板，而是**生成器脚本**

实测 `scripts/podselect.PL` 自带完整的生成逻辑：

```perl
$file = basename($0, '.PL');                 # 产物名 = 自身去掉 .PL

print OUT <<"!GROK!THIS!";                   # 第一段：由 $Config 展开
$Config{'startperl'}
    eval 'exec perl -S $0 "$@"'
        if 0;
!GROK!THIS!

print OUT <<'!NO!SUBS!';                     # 第二段：不展开，原样写入
#############################################################################
# podselect -- command to invoke the podselect function in Pod::Select
...
!NO!SUBS!

close OUT or die "Can't close $file: $!";
chmod 0755, $file or die "Can't reset permissions for $file: $!\n";
```

**必须运行它**，才会在自身旁边写出真正的可执行文件。因此：

- 「把 `.PL` 首行 shebang 换掉就当产物交付」是**根本性误解**——交付出去的仍是
  生成器（`print OUT` 代码原样留着），**根本不是那个工具**；
- 正确做法是**运行生成器**（这正是 MakeMaker `PL_FILES` 所做的事）。

### 产物首行由 `$Config{startperl}` 决定 —— 本平台**不是 `#!`**

生成器写出的是上面第一段（`!GROK!THIS!`），其内容即 `$Config{startperl}`
与一行 `eval 'exec perl -S $0 "$@"'`。**实测本平台**：

```console
$ perl -V:startperl
startperl=': # use perl';
```

故产物首行是 **shell/perl polyglot**：

```sh
: # use perl
    eval 'exec perl -S $0 "$@"'
        if 0;
```

**不是 `#!`**。所以：
- 断言产物以 `#!` 开头会**误杀合法产物**；
- 内核会以 `ENOEXEC` 拒绝该文件，须**经 shell 执行**（shell 的 ENOEXEC 回退会改用
  `sh` 重跑同一文件）——这正是消费方点脚本时的真实路径。Python 若直接
  `execve` 它，会报 `OSError: [Errno 8] Exec format error`。

### 本仓惯例与之的张力

本仓 perl-* 惯例是 **不跑 MakeMaker**（perl-carp 1.50 先例：直接拷 `lib/`）。
于是 `.PL` **永远不会被实例化**——必须由配方自行执行生成器。

## Recommended Solution

### 主方案（priority 1）— **运行生成器** + 校验无生成器残留

在 `build()` 内：

1. 用本仓 perl-* 配方通用候选列表探测解释器（`shutil.which("perl")` →
   `/storage/.../usr/local/bin/perl` → `/data/service/hnp/bin/perl` → `/usr/bin/perl`）；
2. `cd scripts && <perl> <name>.PL` —— 生成器自己写出 `<name>`
   （`$file = basename($0, '.PL')`）；
3. **校验产物不再含生成器标记**（`!NO!SUBS!` / `!GROK!THIS!` / `print OUT`）——
   这是"真的执行了"的判据；若仍命中，说明拿到的还是生成器本体，**须报错**；
4. `chmod 755` 后由 `package()` 放进 `<pkg>/bin/`；`package()` 内**同样**校验
   生成器标记（双保险，且 `package()` 的缺失分支必须是**报错**而非静默跳过）。

**消费者测试须经 shell 真实执行**：`sh <pkg>/bin/<name> -help`，并做一次真实取段。
不要只断言文件存在；也**不要**用 `[perl, script]` 方式调用（那会绕过头部，
掩盖实例化缺陷）。

### 回退方案（priority 2）— 真跑一次 MakeMaker 的 PL_FILES

若生成器逻辑复杂难以直接运行（如需 MakeMaker 提供的环境），可退化到真跑 MakeMaker
的 `PL_FILES` 步骤（仅生成脚本，不安装、不编译 XS）。代价：需 MakeMaker 可用、
引入构建期副作用；须在 `notes.md` 说明为何偏离"不跑 MakeMaker"的惯例。

### 禁止做法

- ❌ 把 `.PL`「改首行」后当产物交付——它是**生成器**，交付的仍不是该工具；
- ❌ 把 `.PL` 直接拷/改名当脚本交付——同上，且首行是上游机器路径；
- ❌ 只断言 `bin/` 下文件存在就认为脚本可用——会漏掉"交付的是生成器"、
  shebang 未实例化、权限位未设等真实缺陷（本仓 R34 要求真实 API 用法）。

## 实测证据（2026-09-17，perl-pod-parser 1.67 适配）

| 项 | 结果 |
|---|---|
| `.PL` 本体 | `scripts/podselect.PL`，**3730 B**；含 `print OUT <<"!GROK!THIS!"` / `print OUT <<'!NO!SUBS!'` / `close OUT` / `chmod 0755, $file` → **是生成器** |
| 运行生成器 | `perl podselect.PL` → 产出 `podselect`，**2524 B**，退出码 0 |
| 产物首行 | `: # use perl`（=`$Config{startperl}` 的 polyglot），**非 `#!`** |
| 直接 execve 产物 | `OSError: [Errno 8] Exec format error`（ENOEXEC，符合 polyglot 预期）|
| **经 shell 执行** | `sh podselect -sections NAME …` → 输出 `=head1 NAME`，**rc=0** ✓ |
| 旧配方的缺陷 | 「只替换首行」产出的文件**仍含 `print OUT` 代码**——即生成器本体（实测该产物 2524 B 但首行为 `: # use perl`… 与生成器本体同源），不是正确实例化 |
| 修复后 | 配方改为**运行生成器** + 校验三处生成器标记；消费者测试经 `sh` 真实执行并取段 |
| 修复后构建 | `conan create` **exit=0**；上游 `prove` **25 测试全过**；consumer API **PASS** |

> **本条目订正了初版的两处错误结论**：(a) 曾称「只换 shebang 即可覆盖绝大多数 `.PL`」
> ——错，`.PL` 必须**运行**；(b) 曾断言产物应为首行 `#!` ——错，本平台产物是 polyglot。

## 测试覆盖边界

本条处理"**`.PL` 生成器未被执行**"。区分相邻情形：

- 纯模块发行版（仅 `lib/`）→ 无本问题（perl-carp 型）；
- 脚本已在 sdist 中为**成品**（无 `.PL` 后缀）→ 只需正常拷入 `bin/`；
- MakeMaker 生成的**其它**构建期产物（如 `.pm` 由 `.pm.PL` 生成）→ 同一机制，
  同样须"运行生成器"，替换项可能更多。

## 关联条目

- 相似：（暂无同族条目）
- 差异：本条要点是"`.PL` 是生成器、产物首行是 polyglot、须经 shell 执行"，
  而非构建系统选择
