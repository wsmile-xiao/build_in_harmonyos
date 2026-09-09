# DRAFT-bison-pure-parser-yylex-signature — bison 3.8 接受已弃用的 %pure_parser 但生成的纯解析器不向 lexer 传 scanner 实参，与 %reentrant flex lexer 的三参 yylex 约定冲突，应迁移为 %define api.pure true 并补 %lex-param

> **Contributor**: GoliWie | **Status**: DRAFT（最终编号由知识库主编确认） | **Updated**: 2026-09-04
> **Severity**: blocking (2) | **Category**: build-tools / bison / flex / parser / autotools / conan
> **Audience**: 在 OHOS/Conan 环境构建含 %pure_parser 语法的 bison/flex 项目（autotools 老项目 ylwrap 流水线）的配方维护者

## 触发（trigger）

- 目标项目用 **bison + flex** 构建 parse（autotools 老流水线：`AC_PROG_YACC`/`AC_PROG_LEX`
  + `ylwrap`，configure 探得 `YACC="bison -y"`、`LEX=flex`）。
- `.y` 含旧式 **`%pure_parser`** 指令（2007 年代上游常见）；`.l` 为
  **`%option reentrant bison-bridge bison-locations`**，并在 `.y` 序言声明三参原型
  `gint yylex (YYSTYPE*, YYLTYPE*, void *yyscanner);`。
- 设备工具链钉死 **bison 3.8.2 / flex 2.6.4 / clang 15.0.4**（/data/service/hnp/bin）。
- 典型现场：libmirage 1.0.0 的 image-ccd/cue/toc 三解析器
  （`image-ccd-parser.c:1546` 处报错）。

## 症状（symptom）

主签名（%reentrant lexer，yylex 调用处）：

```
image-ccd-parser.c:1546:39: error: too few arguments to function call, expected 3, have 2
      yychar = yylex (&yylval, &yylloc);
```

同族变体（非重入 lexer 且原型可见）：

```
pa.c:1129:23: error: too many arguments to function call, expected 0, have 2
```

伴随信号（诊断入口）：

```
image-ccd-parser.y:48.1-7: warning: POSIX Yacc does not support %define [-Wyacc]   （bison -y 模式）
<bison>: warning: deprecated directive: '%error-verbose', use '%define parse.error verbose' [-Wdeprecated]
```

## 机制（root cause）

1. **弃用指令仍被接受，但桥接宏已废**：bison 3.8 接受 `%pure_parser`（仅告警），
   然而 3.x 骨架已废弃 `YYLEX_PARAM` 桥接——`.y` 序言里的 `#define YYLEX_PARAM scanner`
   与三参 `yylex` 原型都**不参与**生成 parser 的调用点签名；调用点形态只由
   "纯度（api.pure）+ `%lex-param`"决定。
2. **纯骨架默认两参调用**：`%pure_parser`/`api.pure` 生效时调用
   `yylex (&yylval, &yylloc)`——不带 scanner。与 `%reentrant` flex 的三参约定冲突，
   即主签名错误（too few arguments, expected 3, have 2）。
3. **反例组（为何必须成对迁移）**：非重入 flex 声明零参 `extern int yylex (void)`——
   保留纯解析器的两参调用在**原型可见**时硬报错 too many arguments（expected 0,
   have 2，探针 pa.c 实测）；**无原型**时靠隐式声明侥幸编译，但 yylval/yylloc 桥接
   被静默丢弃（语义损坏：token 值/位置错乱）。→ 纯解析器与**任何** flex 形态均不再
   默认兼容，修复必须同时覆盖 `.y` 与 `.l` 的纯度约定。

## 修复（rec）

对每个含 `%pure_parser` 的 `.y` **成对迁移**两条指令：替换为
`%define api.pure true` 并紧随追加 **`%lex-param {void *scanner}`**（名字与
`%parse-param` 声明一致）。生成 parser 随即以三参调用
`yylex (&yylval, &yylloc, scanner)`，与 `%reentrant + bison-bridge + bison-locations`
匹配。已验证的一行命令：

```sh
perl -pi -e 's{^%pure_parser$}{%define api.pure true\n%lex-param {void *scanner}}' <each *.y>
```

工程化落地建议走 per-file 补丁（conandata.yml 声明 + build() 内
`apply_conandata_patches`），同型实例：libmirage 1.0.0 补丁 0005
（image-ccd/cue/toc，bison 3.8.2 编译通过）。可选项：`.y` 尚存的
`%error-verbose` 一并替换为 `%define parse.error verbose`，消除弃用警告。

## fallback（退路，含诚实权衡）

**drop-pure-parser-degrade-to-globals**：同时删除 `%pure_parser`（或 api.pure true）
**并**把 lexer 保持/降级为非重入——非纯解析器以 `yylex()` 零参调用、经全局
`yylval`/`yylloc` 传递，与非重入 flex 生成的 `extern int yylex (void)` 匹配。
诚实权衡：牺牲解析器可重入性与线程安全、偏离上游并发语义，仅作退路。
注意：**"只去 reentrant/bison-bridge/bison-locations、保留 %pure_parser 以匹配两参
调用"不成立**（探针实测反向硬报错，见 forbid 4）。

### fallback 编译探针（自包含；全量转录，clang 15.0.4）

```sh
D=$(mktemp -d) && cd $D
printf '%s\n' '%{' 'extern int yylex (void);' '%}' '%pure_parser' '%locations' '%%' 'input : ;' '%%' > pa.y
printf '%s\n' '%{' 'extern int yylex (void);' '%}' '%locations' '%%' 'input : ;' '%%' > pb.y
printf '%s\n' '%option noyywrap' '%%' '. ;' '%%' > l.l
bison -o pa.c pa.y 2>/dev/null && flex -o l.c l.l && clang -c pa.c -o pa.o 2>&1 | grep -m1 error
bison -o pb.c pb.y 2>/dev/null && flex -o l.c l.l && clang -c pb.c -o pb.o && clang -c l.c -o l.o && echo FALLBACK_COMPILES
grep -m1 "yylex (void)" l.c
rm -rf $D
```

逐字实跑输出（2026-09-04；pa 行经 `grep -m1 error` 只留断言行；pb.c 的 2 处
yyerror 隐式声明警告为 stderr 直通全量转录——pb.y 未声明 yyerror，非纯骨架按
%locations 直呼 yyerror，警告文本随 clang 版本而异）：

```
pa.c:1129:23: error: too many arguments to function call, expected 0, have 2
pb.c:1262:7: warning: call to undeclared function 'yyerror'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
      yyerror (YY_("syntax error"));
      ^
pb.c:1377:3: warning: call to undeclared function 'yyerror'; ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
  yyerror (YY_("memory exhausted"));
  ^
2 warnings generated.
FALLBACK_COMPILES
extern int yylex (void);
```

## verification_cmd（主签名复现，自包含）

```sh
D=$(mktemp -d) && cd $D
printf '%s\n' '%pure_parser' '%locations' '%%' 'input : ;' '%%' > t1.y
printf '%s\n' '%define api.pure true' '%lex-param {void *scanner}' '%locations' '%%' 'input : ;' '%%' > t2.y
bison -o t1.c t1.y 2>/dev/null; grep -n "yylex (" t1.c
bison -o t2.c t2.y 2>/dev/null; grep -n "yylex (" t2.c
bison --version | head -1
rm -rf $D
```

预期输出（2026-09-04 补证轮逐字实跑；`/bin/sh` 与 `zsh` 均 rc=0，设备无 /bin/bash）：

```
===UNDER_/bin/sh===                      ===UNDER_zsh===
1123:      yychar = yylex (&yylval, &yylloc);        1123:      yychar = yylex (&yylval, &yylloc);
1123:      yychar = yylex (&yylval, &yylloc, scanner);   1123:      yychar = yylex (&yylval, &yylloc, scanner);
bison (GNU Bison) 3.8.2                   bison (GNU Bison) 3.8.2
sh_rc=0                                   zsh_rc=0
```

t1 两参（无 scanner）= 与 %reentrant lexer 冲突的机理实证；t2 三参（, scanner）=
修复后形态。

## 查重（dedup）

- E402（toybox gzip 长选项）：同为"平台钉死的现代工具 × 上游旧式调用约定"的语义层
  冲突，修复落在工具用法而非平台补丁；本条是 bison/flex 解析器领域的同型问题。
- E546：工具弃用指令的接受但不生效/语义变化类。本条增量：纯度指令的调用点签名
  决定机制（YYLEX_PARAM 废弃 + %lex-param 缺省两参）与"纯解析器 × 任意 flex 形态
  均不默认兼容"的反例组，均未被覆盖。
- knowledge/graph 与 knowledge/drafts 检索（bison/pure_parser/yylex/api.pure/
  %lex-param）无既有条目。

## 证据（evidence）

- libmirage-1.0.0 run：`ci/build-and-test-run1.log` 所在 run 的构建序列
  lm-create-2/3/4/5（lm-create-4 = 只升 api.pure 不加 %lex-param 的失败复现，
  对应 forbid 3；lm-create-5 = 成对迁移后 PASS）。
- 机理探针与 fallback 探针：本文件两段自包含脚本（任何人开新 shell 可跑通）。
- 工具版本：bison 3.8.2 / flex 2.6.4 / clang 15.0.4（/data/service/hnp/bin）。

## 关系（relations）

- principles: P-PATCH-001, P-TOOLCHAIN-001
- similar_to: E402, E546
- prerequisite_of: 无；conflicts_with: 无
