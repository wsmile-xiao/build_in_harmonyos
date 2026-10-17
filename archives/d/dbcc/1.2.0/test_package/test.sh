#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the dbcc executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

echo "[test] dbcc -V"
VERSION_OUT=$(dbcc -V 2>&1) || exit 1
echo "OK: dbcc -V -> $VERSION_OUT"

# Minimal CAN DBC file with one message and one signal (structure follows
# upstream double_signal.dbc so the parser recognizes the message)
cat > "$WORKDIR/min.dbc" <<'DBC'
VERSION ""


NS_ : 
	NS_DESC_
	CM_
	BA_DEF_
	BA_
	VAL_
	CAT_DEF_
	CAT_
	FILTER
	BA_DEF_DEF_
	EV_DATA_
	ENVVAR_DATA_
	SGTYPE_
	SGTYPE_VAL_
	BA_DEF_SGTYPE_
	BA_SGTYPE_
	SIG_TYPE_REF_
	VAL_TABLE_
	SIG_GROUP_
	SIG_VALTYPE_
	SIGTYPE_VALTYPE_

BS_:

BU_: Vector__XXX


BO_ 123 EngineData: 8 Vector__XXX
 SG_ EngineSpeed : 0|16@1+ (1,0) [0|8000] "rpm" Vector__XXX


CM_ BO_ 123 "Engine data message";
DBC

echo "[test] dbcc DBC -> C conversion"
dbcc -o "$WORKDIR" "$WORKDIR/min.dbc" || exit 1
if [ ! -s "$WORKDIR/min.c" ]; then
    echo "FAIL: no min.c generated"
    exit 1
fi
echo "OK: generated $(wc -l < "$WORKDIR/min.c") lines of C"

echo "[test] dbcc DBC -> JSON conversion"
dbcc -j -o "$WORKDIR" "$WORKDIR/min.dbc" || exit 1
if [ ! -s "$WORKDIR/min.json" ]; then
    echo "FAIL: no min.json generated"
    exit 1
fi
echo "OK: generated $(wc -l < "$WORKDIR/min.json") lines of JSON"

echo "ALL DBCC TESTS PASSED"
