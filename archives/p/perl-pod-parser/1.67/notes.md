# perl-pod-parser (Pod::Parser) 1.67 适配笔记

## 概述

Pod::Parser 是 Perl 的 **POD 文档解析基类**（POD = Plain Old Documentation），
供编写 POD 过滤器/转换器使用；发行版内含 6 个模块与 1 个可执行脚本。

- 上游：https://metacpan.org/pod/Pod::Parser
- 版本：1.67
- 构建系统：**Perl**（Makefile.PL / ExtUtils::MakeMaker，本配方不调用）
- 许可：Artistic-2.0
- 编译日期：2026-09-16
- 状态：built

## 三处命名不一致（易混淆）

| 层面 | 名字 |
|---|---|
| CPAN **发行版**名 | `Pod-Parser` |
| **模块**名（主模块）| `Pod::Parser` |
| **conan 包名** | `perl-pod-parser` |

包名按仓内 `perl-*` 命名法归一（与既有的 ~270 个 perl 包一致）。

## 内容（实测自 CPAN tarball）

**`lib/Pod/` 下 6 个模块**：

```
Parser.pm        主模块（基类）
Select.pm        节选（podselect 函数）
PlainText.pm     纯文本转换
InputObjects.pm  段落/命令对象
Find.pm          POD 定位
ParseUtils.pm    解析工具
```

**`scripts/podselect.PL`**：143 行的 `.PL` 模板，上游用 MakeMaker 的 `PL_FILES`
机制生成 `podselect` 可执行文件（替换 `$Config{startperl}` 等变量）。

**`t/pod/`**：16 个 `.t` 文件 + 同名 `.xr` 参照数据。

## 打包方式（沿用仓内 Perl 范式）

配方**不调用 MakeMaker**（与 perl-carp 1.50 一致），而是：

1. `package_type = "application"`（`python-require` 型会让 `conan create` 静默
   跳过构建，见 perl-algorithm-diff 等先例）；
2. `package()` 拷 `lib/` → `lib/perl5`（perl site-lib 约定）；
3. 断言 6 个模块**逐个存在**，防止只拷一层文件而漏掉子目录内容；
4. 配套**软件级 `commands.json`**（R38）。

### `.PL` 脚本的处理（本包特有）

上游靠 MakeMaker 生成 `podselect`；本配方不跑 MakeMaker，故在 `build()` 内
自行生成：**把 `.PL` 首行 shebang（`#!/usr/local/bin/perl`，硬编码的构建机路径）
替换为真实解释器路径**，写入 `scripts/podselect` 并 `chmod 755`，`package()` 时
放到 `bin/`。

不这么做的话，脚本首行会指向一个 OHOS 上不存在的路径，`podselect` 直接不可用。

## 依赖

**无外部依赖**。`META.json` 的 runtime requires 仅：

```
Cwd / File::Basename / Test::More
```

三者都是 **perl 核心模块**，随解释器分发 → 不需要 `requires()`。这与仓内既有
perl 包一致（perl-carp / perl-json-pp / perl-scope-guard 均不声明依赖）。

## 上游测试

`t/pod/*.t`，16 个文件 25 个用例，实测全过：

```
All tests successful.
Files=16, Tests=25,  2 wallclock secs
Result: PASS
```

`build()` 内以 `prove -l t/pod` 执行并回填真实结果（R51）。`prove` 与
`Test::More` 均属核心分发，故不做额外 skip 逻辑（若解释器被裁剪而缺
`Test::More`，配方会**显式输出理由**再跳过，不静默）。

## 消费者测试（test_package）

`test_package/test_pod_parser.py`（通过 perl 解释器驱动，与 perl-carp
test_package 同思路），断言全部基于**实测**：

| 组 | 断言 |
|---|---|
| 模块齐全 | 6 个 `.pm` 逐个存在 |
| **模块加载 + 版本** | 6 个模块 `require` 成功；Parser/Select/InputObjects/Find/ParseUtils 均 **1.67**，而 **PlainText 为 2.07**（上游不一致，**显式固化**）|
| **子类化解析真实文档** | 继承 `Pod::Parser` 实现 `command`/`verbatim`/`textblock`/`interior_sequence`，`parse_from_file` 解析含 `=head1`/`=head2`/缩进代码/`B<>` 的文档 |
| 回调语义 | `CMD:head1` / `CMD:head2` 出现且带正确行号 |
| **参数类型（反直觉点）** | `command`/`verbatim` 的第 3 个参数是**纯字符串**（`ref()` 为空），**不是** `Pod::InputObjects` 对象 |
| `Pod::Select::podselect` | 抽取 `NAME` 节，输出非空且首行为 `=head1 NAME` |
| `Pod::Find` | `pod_where` / `contains_pod` 存在（**无** `find_pod`，实测确认）|
| 生成的 podselect | 若 `bin/podselect` 存在则校验可执行且能运行 |

> 探针阶段踩到的两个**反直觉点**（已写进断言注释）：
> ① 回调第 3 参是字符串而非对象；② `Pod::Parser` **没有** `parse_from_string`，
> 只有 `parse_from_file` / `parse_from_filehandle` / `parse_text` / `parse_paragraph`。

## 验证结果

```
conan create archives/p/perl-pod-parser/1.67 --build=missing \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
→ exit=0
```

| 项 | 实测结果 |
|---|---|
| `conan create` | **exit=0**，Package created |
| `.PL` 生成 | `generated podselect from podselect.PL (perl=/storage/Users/currentUser/usr/local/bin/perl)` |
| 上游测试 | `All tests successful. Files=16, Tests=25 ... Result: PASS`（**25/25**）|
| 消费者测试 | `perl-pod-parser (Pod::Parser 1.67) consumer API: PASS`，含 `podselect executable present and runnable` |

### 实测订正：verbatim 段落含换行导致日志被拆行

消费者测试初版断言失败：

```
AssertionError: ['CMD:head1|line=1|ref=SCALAR', 'TXT:Foo - demo', 'CMD:head2|line=5|ref=SCALAR',
                 'VERB:  indented code', '', '|ref=SCALAR', 'TXT:Some B<bold> text.']
```

根因：**verbatim 段落自身含内嵌换行**，写入 Perl 日志数组后一条记录被拆成多行
（可见 `'VERB:  indented code'`、`''`、`'|ref=SCALAR'` 三行），
导致 `ref=SCALAR` 那行不带 `VERB:` 前缀而断言失败。
修法：Perl 侧加 `_one()` 把条目内 `\n` 转义为字面量 `\\n`，保证**一条日志一行**。

## 注意事项

1. **不调用 MakeMaker**（沿用仓内 Perl 范式），故 `.PL` 需自行生成；
2. **`__version__` 类断言要按模块分别写**——同发行版内 PlainText 是 2.07、
   其余是 1.67，统一断言 1.67 会失败；
3. 回调第 3 参是**字符串**，别按"应该是对象"去写（`->text` 会报
   `Can't locate object method "text"`）；
4. `perl-*` 包统一用 `package_type = "application"` + `commands.json`（R38）。
