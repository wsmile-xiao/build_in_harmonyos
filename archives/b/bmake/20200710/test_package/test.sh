#!/data/service/hnp/bin/bash
set -eu

test -f "$MAKESYSPATH/sys.mk"

cat > Makefile <<'EOF'
all:
	@printf '%s\n' bmake-test-package-ok
EOF

test "$(bmake -f Makefile)" = "bmake-test-package-ok"
printf '%s\n' '[test] bmake consumer test passed'
