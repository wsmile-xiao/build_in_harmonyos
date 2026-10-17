#!/data/service/hnp/bin/bash
set -euo pipefail

# bsdmake consumer test: exercise core make functionality
# (rule execution, variable expansion, .PHONY, exit status) using the
# packaged bsdmake binary and its bundled system rules.

cd "$(mktemp -d)"
trap 'rm -rf "$PWD"' EXIT

# 1. Variable expansion + rule execution
cat > Makefile <<'EOF'
GREETING := hello-bsdmake
all:
	@printf '%s\n' "$(GREETING)"
EOF

out="$(bsdmake -m "$MAKESYSPATH" -f Makefile)"
test "$out" = "hello-bsdmake"
printf '%s\n' '[test] variable expansion + rule execution passed'

# 2. .PHONY / dependency graph
cat > Makefile <<'EOF'
.PHONY: all step1 step2
all: step1 step2
step1:
	@printf '%s\n' one
step2:
	@printf '%s\n' two
EOF

out="$(bsdmake -m "$MAKESYSPATH" -f Makefile)"
test "$out" = "$(printf 'one\ntwo')"
printf '%s\n' '[test] dependency graph passed'

# 3. Error propagation (nonexistent target)
cat > Makefile <<'EOF'
all:
	@true
EOF

if bsdmake -m "$MAKESYSPATH" -f Makefile no-such-target >/dev/null 2>&1; then
    echo "error: nonexistent target should fail" >&2
    exit 1
fi
printf '%s\n' '[test] error propagation passed'

# 4. system rules availability (sys.mk bundled)
test -f "$MAKESYSPATH/sys.mk"
printf '%s\n' '[test] MAKESYSPATH sys.mk passed'

printf '%s\n' '[test] bsdmake consumer test passed'
