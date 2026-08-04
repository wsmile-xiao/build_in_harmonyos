#!/bin/sh
set -eu

uglifyjs=$1

version=$("$uglifyjs" --version)
test "$version" = "uglify-js 3.19.3"

cat > input.js <<'EOF'
(function () {
    function add(first, second) {
        return first + second;
    }
    console.log(add(20, 22));
}());
EOF

"$uglifyjs" input.js --compress --mangle --output output.js
test -s output.js
test "$(node --jitless output.js)" = "42"

stdin_result=$(printf '%s' 'function square(value) { return value * value; } console.log(square(6));' \
    | "$uglifyjs" --compress --mangle)
test -n "$stdin_result"
test "$(printf '%s' "$stdin_result" | node --jitless)" = "36"

echo "uglify consumer tests passed"
