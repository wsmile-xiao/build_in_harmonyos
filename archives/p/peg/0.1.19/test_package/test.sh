#!/data/service/hnp/bin/bash
set -euo pipefail

peg -V
leg -V

printf '%s\n' 'start <- "hello" "world" { printf("matched\\n"); }' > test_grammar.peg
peg -o generated.c test_grammar.peg

[ -s generated.c ]
grep -q 'yyparse' generated.c
grep -q 'matched' generated.c

printf '%s\n' 'peg/leg functional test passed'
