#!/bin/sh
set -eu

uglifycss=$1

version=$("$uglifycss" --version)
test "$version" = "uglifycss 0.0.29"

stdin_result=$(printf '%s' '/* comment */ .button { color: red; margin: 0px 0px 0px 0px; }' | "$uglifycss")
test "$stdin_result" = '.button{color:red;margin:0}'

cat > input.css <<'EOF'
.header { padding: 0px 0px 0px 0px; color: #ff0000; }
EOF

file_result=$("$uglifycss" input.css)
test "$file_result" = '.header{padding:0;color:red}'

"$uglifycss" --output output.css input.css
test "$(cat output.css)" = '.header{padding:0;color:red}'

echo "uglifycss consumer tests passed"
