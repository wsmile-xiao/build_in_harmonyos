#!/data/service/hnp/bin/bash
# 消费者视角测试：只使用已安装的包（bin/peg、bin/leg 由包 runenv 注入 PATH），
# 不接触源码树与构建产物。断言全部基于真实进程退出码与生成物内容。
set -euo pipefail

# OHOS 上 /tmp 可能是只读的（也见仓库既有笔记），因此优先 TMPDIR，其次当前
# 目录；两者都不可写才失败。始终在临时目录内工作，结束即清理，不污染源码树。
tmpbase="${TMPDIR:-}"
if [ -z "$tmpbase" ] || [ ! -w "$tmpbase" ]; then
    tmpbase="$(pwd)"
fi
workdir="$(mktemp -d "$tmpbase/leg-test.XXXXXX")"
trap 'rm -rf "$workdir"' EXIT
cd "$workdir"

# ── 1. 两个命令都必须存在于 PATH 且能报出版本 ─────────────────────────────
peg_path="$(command -v peg)"
leg_path="$(command -v leg)"
echo "peg: $peg_path"
echo "leg: $leg_path"

peg -V | grep -q '^peg version 0\.1\.18$'
leg -V | grep -q '^leg version 0\.1\.18$'

# ── 2. peg：PEG 文法 → C 源码 ─────────────────────────────────────────────
cat > grammar.peg <<'EOF'
start	<- body '.' { printf("done\n"); }
body	<- 'a' { printf("a1 "); } 'b'
EOF

peg -o generated_peg.c grammar.peg
test -s generated_peg.c
grep -q 'yyparse' generated_peg.c      # 生成了可用的解析器入口
grep -q 'done' generated_peg.c         # 语义动作被原样搬运
grep -q 'a1 ' generated_peg.c

# ── 3. leg：LEG 文法（%{ %} 头部 + %% 尾部）→ C 源码 ──────────────────────
cat > grammar.leg <<'EOF'
%{
#include <stdio.h>
%}

start = < [a-z]+ > { printf("word: %s\n", yytext); }

%%

int main(void)
{
  while (yyparse())
    ;
  return 0;
}
EOF

leg -o generated_leg.c grammar.leg
test -s generated_leg.c
grep -q 'yyparse' generated_leg.c      # LEG 前端同样产出 yyparse
grep -q 'word: %s' generated_leg.c     # 动作体被搬运
grep -q 'yytext' generated_leg.c       # 捕获变量可用
grep -q 'int main' generated_leg.c     # %% 之后的用户代码被搬运

printf '%s\n' 'peg/leg consumer test passed'
