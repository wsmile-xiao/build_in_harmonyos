# DRAFT-ohos-perl-script-package-conan-adaptation — OHOS 上适配纯 Perl 脚本包：shebang 改 `env perl`（并去掉 `-w`）+ 自行补齐 conan perl 的模块路径

> **Contributor**: ohpcd | **Status**: DRAFT | **Updated**: 2026-09-12
> **Severity**: 🟡 medium | **Category**: perl / conan / packaging / shebang / ohos

## 与既有条目的差异边界（已逐条核对）

| 既有条目 | 关系 |
|---------|------|
| **`DRAFT-ohos-autotools-maintainer-noregen`** | 也提到「`self.run` 会重载 conanbuildenv 覆盖 `os.environ`」与「命令内内联 PERL5LIB」。但其语境是 **automake 版本冲突**（conanbuildenv 的 1.16 排在 1.18 前 → version mismatch）。本条讲**另一个成因**：conan 的 perl 包**内建 `@INC`** 被判成 `//lib/perl5/...`（编译期前缀解析为空 → 双斜杠根路径，全部不存在），导致**连核心模块**都加载不了；并给出该条目未涉及的两项判据（选目录须以 `strict.pm` 判定、桩目录放 `perl` 包装器且 `-I` 优先于 `PERL5LIB`）。二者成因与判据不同，互补 |
| **`DRAFT-ohos-intltool-toolchain-stub`** | 讲 intltool 工具链 stub（`XML::Parser` stub + `PERL5LIB` 前置），面向 **autotools 构建期工具缺失**；本条面向**纯 Perl 脚本包的分发**（shebang / 安装 / 消费者调用），角度不同（实测该条目对 `self.run` 提及 **0**）|

> 查重（2026-09-12）：`env perl -w` 命中 **0**；19 条含 `#!/usr/bin/env` 的条目中**无一**讲 `-w` 陷阱；`PerlIO::encoding` / `Unknown PerlIO layer` / `//lib/perl5` / `perl 包装器` 命中 **各 0**；`Devel::Cover` 命中 **0**。

## Scope（何时用）

在 OHOS（或任何用 conan 分发脚本包的环境）上适配**纯 Perl 脚本包**（单文件 `.pl`、无编译）。也适用于任何「在 recipe 内 `self.run()` 调用 conan 提供的解释器/工具」的场景。

## 根因：两类**互相独立**的坑

### ① shebang 的两处问题（一次改对，否则装出的脚本不可执行）

- 上游写死 `#!/usr/bin/perl`（或 `#!/usr/bin/perl -w`），而 **OHOS 无 `/usr/bin/perl`** —— perl 由 ohpcd 的 perl 包提供，位于包内 `bin/`。故须改为 `#!/usr/bin/env perl`，由 PATH 解析（仓库内已有 24 处采用该写法）。
- ⚠️ **不能只把 `/usr/bin/perl` 换成 `env perl` 而保留 `-w`**：

```
#!/usr/bin/env perl -w     ← 错误写法
```

内核只把 shebang **首个空白之后的全部内容当作一个参数**传给解释器 → `env` 收到的是单个字符串 `"perl -w"`，它会去找一个名叫 `perl -w` 的程序 → **必然失败**。实测：

```
$ ./t1.pl          # shebang = #!/usr/bin/env perl -w
env: exec perl -w: No such file or directory
```

必须**一并去掉 `-w`**（脚本内多已 `use warnings`，无功能损失）。

> 附带说明：`#!/usr/bin/perl -w`（**绝对路径**带 `-w`）是**正常**的 —— 内核把 `/usr/bin/perl` 当解释器、`-w` 当它的单个参数。问题只出在中间夹了 `env` 这一层（env 收到的整串必须是**程序名**）。

### ② conan 的 perl 包内建 `@INC` 是坏的，必须自己补齐模块路径

实测（不设 `PERL5LIB`）：

```bash
$ env -u PERL5LIB <perl_pkg>/bin/perl -e 'print "$_\n" for @INC'
//lib/perl5/site_perl/5.42.2/aarch64-linux-thread-multi
//lib/perl5/site_perl/5.42.2
//lib/perl5/5.42.2/aarch64-linux-thread-multi
//lib/perl5/5.42.2
```

即**编译期前缀被解析成了空串 → 双斜杠根路径**，而这些路径**全部不存在**。后果：**连核心模块都加载不了**：

```bash
$ env -u PERL5LIB <perl> -e 'require strict'
Can't locate strict.pm in @INC
```

故不能裸用该 perl，必须显式提供 `lib/perl5/<版本>` 及其 arch 子目录。

典型表现（triehash 实测）：

```
Unknown PerlIO layer "encoding"      ← triehash.pl 用 :encoding(utf8)，而 PerlIO::encoding 未被 @INC 覆盖
Wide character in printf at ... .pl line 663   ← 连带警告，污染标准输出
```

→ 使上游测试的期望输出 **diff 失败**。

> ⚠️ **关键判读**：此时失败**不是被测程序的功能缺陷**，而是构建期 perl 环境不完整。若误判成"库在 OHOS 有问题"会走错方向。

### ⚠️ 不要指望靠环境变量（`PERL5LIB`）把这件事送进去

实测 conanbuildenv **确实**导出了完整的 `PERL5LIB`（含各子目录），其写法是：

```sh
export PERL5LIB="<conan 的长列表>${PERL5LIB:+:$PERL5LIB}"
```

注意这是**追加**（把已有值接在后面），**不是覆盖**。但因其自己那串长列表排在**前面**、且其中混有坏的 `//lib/perl5` 条目，实测**仍会失败**（报 PerlIO/XS 加载错误）。

→ 结论：问题不是"conan 没注入"，而是"**注入的内容里含坏路径**"。与其和 env 的**顺序/作用域**较劲，不如**绕开 env**。

★ 决定性依据：**`-I` 的优先级高于 `PERL5LIB`**。实测：即便 `PERL5LIB` 给的是错值，只要 `-I<正确目录>`，核心模块即可加载：

```bash
$ PERL5LIB="/nonexistent" <perl> -I<vdir> -I<archdir> -MPerlIO::encoding -e 'print "OK"'
OK
```

这正是下文「`perl` 包装器」稳健的根据。

### 另一个坑：定位 perl lib 目录不能"逆序取第一个"

`lib/perl5` 下同时存在版本目录（如 `5.42.2`，含核心模块）与 `site_perl`；**逆序会把 `site_perl` 排在前面**，而它**不含核心模块**（无 `strict.pm`）→ 照样失败。应以「**是否含 `strict.pm`**」判定版本目录。

## 方案：四步，缺一不可

### ① shebang 改 `#!/usr/bin/env perl` 且去掉 `-w`

做成 conandata 的 portability patch，并在 `build()` 里**自校**首行是否真被改写（防补丁静默失效后装出不可执行的脚本）。

### ② 显式补齐 perl 的模块搜索路径

不要寄望于 conanbuildenv 的 `PERL5LIB`（理由见上）。自行定位版本目录 —— **以是否含 `strict.pm` 判定**：

```python
base = f"{perl_pkg}/lib/perl5"
libs = []
for name in sorted(os.listdir(base)):
    vdir = f"{base}/{name}"
    if not os.path.isdir(vdir):
        continue
    if os.path.isfile(f"{vdir}/strict.pm"):
        libs.insert(0, vdir)      # 版本目录（含核心模块）优先
    else:
        libs.append(vdir)         # 如 site_perl
    # 再带上 arch 子目录（如 aarch64-linux-thread-multi）
```

### ③ 用「桩目录内的 `perl` 包装器」把路径钉死

在桩目录写一个可执行 `perl`：

```sh
#!/bin/sh
exec "<真 perl>" -I<lib1> -I<lib2> ... "$@"
```

并把它所在目录**前置到 PATH**。脚本 shebang 经 `env perl` 命中的即我们的包装器 —— 而 **`-I` 优先于 `PERL5LIB`**（见上），故该做法对环境里 `PERL5LIB` 的取值/顺序**不敏感**。

再内联 `PATH` 确保 shebang 能找到包装器即可（`PERL5LIB` 不必再内联）：

```python
self.run(f'PATH="{stub}{sep}{perl_bin}{sep}$PATH" sh "{run_sh}"')
```

### ④ 包装与分发

脚本装为 `bin/<tool>`（去掉 `.pl` 后缀）并 `chmod +x`；`package_info` 声明 `bindirs=["bin"]`；可执行文件类包按 **R38** 建软件级 `commands.json`。

### 记录口径

把「为何要去掉 `-w`」「为何要自带 `perl` 包装器（`-I` 优先于 `PERL5LIB`）」写进配方注释 —— 否则后续维护者很容易"顺手"把 `-w` 加回去或删掉包装器，从而装出不可执行的脚本。

## 备选（fallback）

若确实无法补齐 perl 运行环境（目标环境根本没有可用 perl），**不要**伪装测试通过：把 test_package 的运行时执行如实标 **SKIP** 并在 `test_note` 说明原因（R34：绝不把"跑不了"当"通过"）。

> 注意区分：本条场景通常**可以**修好（补齐模块路径即可），故应先尝试 ①②③。

## 禁止

- ❌ **`#!/usr/bin/env perl -w`** —— 内核把 shebang 首个空白之后的全部内容当作**一个参数**传给解释器 → `env` 收到 `"perl -w"` 并去找名为 `perl -w` 的程序 → 必然失败；且因发生在内核 `exec` 阶段、错误信息**不含脚本名**，极难定位
- ❌ **逆序/按名称取 `lib/perl5` 的第一个目录** —— 可能选中 `site_perl`（**不含 `strict.pm`**）→ 依然加载不了核心模块，还会让"已经给了 PERL5LIB"的假设误导排查方向
- ❌ **依赖 conanbuildenv 的 `PERL5LIB` 就够了** —— 它**确实**导出了长列表（且是**追加**而非覆盖），但排在前面的是坏的 `//lib/perl5` 条目 → 实测仍失败；误以为"conan 已经帮我们注入了"会让人不再自行补齐路径
- ❌ **把 `Unknown PerlIO` / `Wide character` 当成库的缺陷/不兼容** —— 它们来自构建期 perl 环境不完整（内建 `@INC` 为坏的 `//lib/perl5` 路径、缺核心模块），不是被测程序的功能问题

## 实证

- **triehash/0.3.1（PR #9650）**：
  - 上游 shebang `#!/usr/bin/perl -w` → OHOS 无 `/usr/bin/perl`；改为 `#!/usr/bin/env perl` **并去掉 `-w`** 后方可执行
    - 对照实测：`#!/usr/bin/env perl -w` → `env: exec perl -w: No such file or directory`（证实该写法必败）
  - conan perl 包（`perl/5.42.2`）的**内建 `@INC`** 实测为 `//lib/perl5/site_perl/5.42.2` / `//lib/perl5/5.42.2`（**均不存在**）；`env -u PERL5LIB <perl> -e 'require strict'` → `Can't locate strict.pm in @INC`（连核心模块都加载不了）
  - 未补齐路径时 triehash.pl 的 `:encoding(utf8)` 报 `Unknown PerlIO layer "encoding"` 并连带 Wide character 警告污染输出，导致上游用例 diff 失败（**非被测程序缺陷**）
  - ⚠️ **更正**：conanbuildenv **确实**导出了长 `PERL5LIB`（**追加式** `${PERL5LIB:+:$PERL5LIB}`，**不是覆盖**），但排在前面的是坏的 `//lib/perl5` 条目 → 实测仍失败。故问题不是"没注入"，而是"注入的内容里含坏路径"
  - ✅ 决定性依据：**`-I` 优先于 `PERL5LIB`** —— 给错的 `PERL5LIB` + 正确的 `-I`，核心模块仍可加载。据此采用「桩目录 `perl` 包装器（带 `-I`）」+ 内联 `PATH`，上游 **7/7 用例通过**（并做阴性对照确认套件非空转）
  - 选目录须以 `strict.pm` 判定（逆序会选中无核心模块的 `site_perl`）
