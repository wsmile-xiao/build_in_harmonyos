#!/usr/bin/env sh
set -eu
if (set -o pipefail) 2>/dev/null; then
  set -o pipefail
fi

emacs=${1:?emacs executable path required}
work=${TMPDIR:-.}/emacs-test-package-$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

: "${EMACSLOADPATH:?EMACSLOADPATH is required}"
: "${EMACSDATA:?EMACSDATA is required}"
: "${EMACSDOC:?EMACSDOC is required}"
: "${EMACSPATH:?EMACSPATH is required}"
test -d "$EMACSLOADPATH"
test -d "$EMACSDATA"
test -f "$EMACSDOC"
test -d "$EMACSPATH"

"$emacs" -Q --batch --eval '(princ emacs-version)' > "$work/version.txt"
grep '^29\.1' "$work/version.txt" >/dev/null

cat > "$work/probe.el" <<'EOF'
(defun emacs-conan-probe ()
  (+ 19 10))
(unless (= (emacs-conan-probe) 29)
  (error "unexpected arithmetic result"))
EOF

"$emacs" -Q --batch \
  --eval "(setq byte-compile-dest-file-function (lambda (_) \"$work/probe.elc\"))" \
  --funcall batch-byte-compile "$work/probe.el"

test -f "$work/probe.elc"
echo "emacs batch mode and byte compilation OK"
