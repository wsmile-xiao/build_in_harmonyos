#!/bin/sh
# test_package/test.sh — consumer regression tests for menhir 20260209
# Usage: /bin/sh test.sh <menhir-prefix> <ocaml-prefix>
# POSIX sh only (runs under OHOS mksh and under bash/sh in CI).
# All tools are addressed by absolute path; no PATH assumptions.
#
# NOTE: `set -e` / pipefail are intentionally not used: this harness asserts
# negative cases (commands that MUST return non-zero) and counts every
# failure instead of aborting on the first one; failures are aggregated and
# reported via the final RESULT line and exit status.
set -u

MENHIR_PREFIX="${1:-}"
OCAML_PREFIX="${2:-}"

MENHIR="$MENHIR_PREFIX/bin/menhir"
OCAMLOPT="$OCAML_PREFIX/bin/ocamlopt"

if [ -z "$MENHIR_PREFIX" ] || [ ! -x "$MENHIR" ]; then
    echo "FAIL: menhir binary not found: $MENHIR"
    exit 1
fi
if [ -z "$OCAML_PREFIX" ] || [ ! -x "$OCAMLOPT" ]; then
    echo "FAIL: ocamlopt not found: $OCAMLOPT"
    exit 1
fi

# The packaged ocamlopt has a stale baked-in stdlib path after Conan cache
# relocation (see merged ocaml recipe notes); OCAMLLIB fixes it.
export OCAMLLIB="$OCAML_PREFIX/lib/ocaml"
PATH="$OCAML_PREFIX/bin:$MENHIR_PREFIX/bin:$PATH"
export PATH

total=0
failed=0

pass() { total=$((total + 1)); echo "PASS: $1"; }
fail() { total=$((total + 1)); failed=$((failed + 1)); echo "FAIL: $1"; }
assert_rc() { # <label> <expected-rc> <actual-rc>
    if [ "$3" -eq "$2" ]; then pass "$1"; else fail "$1 (expected rc=$2, got rc=$3)"; fi
}

W="_menhir_consumer_test"
rm -rf "$W"
mkdir -p "$W/code" "$W/table" || { echo "FAIL: cannot create test workdir"; exit 1; }

# --- fixture: small calculator grammar + hand-written driver ---
cat > "$W/code/test.mly" <<'GRAMMAR'
%token <int> INT
%token PLUS EOF
%start <int> main
%type <int> expr
%%
main: e = expr EOF { e }
expr: n = INT { n }
    | e = expr PLUS n = INT { e + n }
GRAMMAR

cat > "$W/bad.mly" <<'GRAMMAR'
%token A
%start main
%%
main: A UNDECLARED { () }
GRAMMAR

cat > "$W/code/main.ml" <<'DRIVER'
let tokenize s =
  let n = String.length s in
  let rec go i acc =
    if i >= n then List.rev (Test.EOF :: acc)
    else match s.[i] with
      | ' ' | '\t' -> go (i + 1) acc
      | '+' -> go (i + 1) (Test.PLUS :: acc)
      | c when c >= '0' && c <= '9' ->
          let j = ref i in
          while !j < n && s.[!j] >= '0' && s.[!j] <= '9' do incr j done;
          go !j (Test.INT (int_of_string (String.sub s i (!j - i))) :: acc)
      | _ -> failwith "invalid character"
  in
  go 0 []

let () =
  let toks = Array.of_list (tokenize Sys.argv.(1)) in
  let pos = ref 0 in
  let next _lexbuf = let t = toks.(!pos) in incr pos; t in
  try
    let result = Test.main next (Lexing.from_string "") in
    Printf.printf "%d\n" result
  with Test.Error ->
    prerr_endline "syntax error";
    exit 2
DRIVER

cp "$W/code/test.mly" "$W/table/test.mly"
cp "$W/code/main.ml" "$W/table/main.ml"

# --- 1: version ---
v="$("$MENHIR" --version 2>&1)"; rc=$?
assert_rc "menhir --version exits 0" 0 "$rc"
case "$v" in
  *20260209*) pass "menhir --version reports 20260209" ;;
  *) fail "menhir --version reports 20260209 (got: $v)" ;;
esac

# --- 2: code back-end generates parser sources ---
( cd "$W/code" && "$MENHIR" --code test.mly ) > "$W/code/gen.log" 2>&1
assert_rc "menhir --code generates parser" 0 "$?"
if [ -f "$W/code/test.ml" ] && [ -f "$W/code/test.mli" ]; then
    pass "menhir --code produced test.ml + test.mli"
else
    fail "menhir --code produced test.ml + test.mli"
    cat "$W/code/gen.log"
fi

# --- 3: compile + run generated parser (code back-end) ---
( cd "$W/code" && "$OCAMLOPT" test.mli test.ml main.ml -o calc ) > "$W/code/build.log" 2>&1
rc=$?
assert_rc "ocamlopt compiles code-backend parser + driver" 0 "$rc"
[ "$rc" -eq 0 ] || cat "$W/code/build.log"
out="$("$W/code/calc" '1+2+4' 2>&1)"; rc=$?
assert_rc "calc accepts '1+2+4'" 0 "$rc"
if [ "$out" = "7" ]; then pass "calc computes 1+2+4 = 7"; else fail "calc computes 1+2+4 = 7 (got: $out)"; fi

# --- 4: parser rejects invalid input (negative control) ---
"$W/code/calc" '1+' > "$W/code/reject.log" 2>&1
assert_rc "calc rejects '1+' (parser Error)" 2 "$?"

# --- 5: grammar with undeclared token is rejected at generation time ---
"$MENHIR" --code "$W/bad.mly" > "$W/bad.log" 2>&1
rc=$?
if [ "$rc" -ne 0 ] && grep -q "UNDECLARED" "$W/bad.log"; then
    pass "menhir rejects grammar with undeclared token"
else
    fail "menhir rejects grammar with undeclared token (rc=$rc)"
    cat "$W/bad.log"
fi

# --- 6: table back-end + link against packaged menhirLib ---
# Note: OCaml native link order puts archives BEFORE the modules that use them.
( cd "$W/table" && "$MENHIR" --table test.mly ) > "$W/table/gen.log" 2>&1
assert_rc "menhir --table generates parser" 0 "$?"
( cd "$W/table" && "$OCAMLOPT" -I "$MENHIR_PREFIX/lib/menhirLib" \
    "$MENHIR_PREFIX/lib/menhirLib/menhirLib.cmxa" \
    test.mli test.ml main.ml \
    -o calc_table ) > "$W/table/build.log" 2>&1
rc=$?
assert_rc "ocamlopt links table-backend parser with menhirLib" 0 "$rc"
[ "$rc" -eq 0 ] || cat "$W/table/build.log"
out_table="$("$W/table/calc_table" '20+22' 2>&1)"; rc=$?
assert_rc "calc_table accepts '20+22'" 0 "$rc"
if [ "$out_table" = "42" ]; then pass "calc_table computes 20+22 = 42"; else fail "calc_table computes 20+22 = 42 (got: $out_table)"; fi

echo "----------------------------------------"
echo "menhir consumer tests: $((total - failed))/$total passed"
if [ "$failed" -ne 0 ]; then
    echo "RESULT: FAIL"
    exit 1
fi
echo "RESULT: PASS"
rm -rf "$W"
exit 0
