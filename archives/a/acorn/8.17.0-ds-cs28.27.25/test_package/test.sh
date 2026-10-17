#!/bin/sh
set -eu

cat > input.js <<'EOF'
const answer = 40 + 2
EOF

acorn --ecma2020 input.js > ast.json
test -s ast.json
node -e 'const ast=require("./ast.json"); if (ast.type !== "Program" || ast.body.length !== 1 || ast.body[0].type !== "VariableDeclaration") process.exit(1)'
