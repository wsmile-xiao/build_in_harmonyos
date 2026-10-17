#!/bin/sh
# test.sh — pasco 20040505 消费者测试：真执行打包后的 `pasco` 二进制。
# 断言全部来自实测读数（notes.md「CLI 真值矩阵」），本机只有 /bin/sh，故用 POSIX sh。
# 输入是合成的 index.dat（上游样本为 Windows 专有格式，本平台不可得），构造依据见 gen_index_dat.py。
set -u
D=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
T="${TMPDIR:-/tmp}/pasco-test-$$"
mkdir -p "$T" || exit 1
trap 'rm -rf "$T"' EXIT INT TERM
TAB=$(printf '\t')

assert=0; pass=0; fail=0
ok()   { assert=$((assert+1)); pass=$((pass+1)); printf 'ok   %s\n' "$1"; }
bad()  { assert=$((assert+1)); fail=$((fail+1)); printf 'FAIL %s\n' "$1"; }
run()  { id=$1; want=$2; shift 2
         "$@" > "$T/$id.out" 2> "$T/$id.err"; got=$?
         if [ "$got" = "$want" ]; then ok "[$id] exit=$got (want $want)"
         else bad "[$id] exit=$got want=$want"; sed -n '1,3p' "$T/$id.err"; fi; }
has()  { id=$1; pat=$2
         if grep -qF -- "$pat" "$T/$id.out" 2>/dev/null; then ok "[$id] stdout 含 $pat"
         else bad "[$id] stdout 缺 $pat"; fi; }
nohas(){ id=$1; pat=$2
         if grep -qF -- "$pat" "$T/$id.out" 2>/dev/null; then bad "[$id] stdout 不该含 $pat"
         else ok "[$id] stdout 无 $pat"; fi; }
clean_err() { id=$1
         if [ -s "$T/$id.err" ]; then bad "[$id] stderr 非空（上游把错误写在 stdout）"; else ok "[$id] stderr 空"; fi; }
nf()   { id=$1; sep=$2
         awk -F"$sep" '/example\.com/{print NF; exit}' "$T/$id.out"; }

python3 "$D/gen_index_dat.py" "$T/index.dat" >/dev/null || { echo "FATAL 样本生成失败"; exit 1; }

# 1) 无参数：usage 走 stdout，退出码 -2 -> 254
run noargs 254 pasco
has noargs 'Usage:  pasco [options] <filename>'
has noargs '-t Field Delimiter (TAB by default)'
clean_err noargs

# 2) 合法合成样本：退出 0，报告版本 5.2，表头 7 列 + 恰好一条 URL 记录（TAB 分隔）
run valid 0 pasco "$T/index.dat"
has valid 'History File:'
has valid 'Version: 5.2'
has valid 'HTTP HEADERS'
has valid 'http://example.com/index.html'
clean_err valid
[ "$(nf valid "$TAB")" = 7 ] && ok "valid 记录行 TAB 字段数=7" || bad "valid 记录行 TAB 字段数=$(nf valid "$TAB") want=7"
rec=$(awk -F"$TAB" '/example\.com/{print $1 "|" $4 "|" $5; exit}' "$T/valid.out")
[ "$rec" = "URL||" ] && ok "valid 首字段=URL 且空 FILETIME 的访问/文件名字段为空" || bad "valid 记录形态=$rec want=URL||"
rows=$(awk '/example\.com/{n++} END{print n+0}' "$T/valid.out")
[ "$rows" = 1 ] && ok "valid 记录条数=1（哈希表链遍历一条）" || bad "valid 记录条数=$rows want=1"

# 3) -t 自定义分隔符：同一记录改为逗号分隔，仍是 7 字段
run delim 0 pasco -t , "$T/index.dat"
[ "$(nf delim ',')" = 7 ] && ok "delim -t , 记录行逗号字段数=7" || bad "delim 字段数=$(nf delim ',') want=7"
has delim 'TYPE,URL,MODIFIED TIME'

# 4) -d undelete 路径：跳过哈希表按 0x80 块步进，仍捞出同一条记录
run undelete 0 pasco -d "$T/index.dat"
has undelete 'http://example.com/index.html'
[ "$(nf undelete "$TAB")" = 7 ] && ok "undelete 记录行 TAB 字段数=7" || bad "undelete 字段数=$(nf undelete "$TAB") want=7"

# 5) 非法选项：clang 运行时把诊断写 stderr，pasco 自身 usage 写 stdout，退出码 -1 -> 255
run badopt 255 pasco -q "$T/index.dat"
has badopt 'Usage:  pasco [options] <filename>'
if grep -qF 'unrecognized option: q' "$T/badopt.err"; then ok "badopt stderr 含 unrecognized option: q"
else bad "badopt stderr 缺 unrecognized option 诊断"; fi

# 6) 文件打不开：ERROR 文本在 stdout（不是 stderr），退出码 -3 -> 253
run nofile 253 pasco "$T/nonexistent-index.dat"
has nofile 'ERROR - The index.dat file cannot be opened!'

# 7) 非 index.dat 输入：上游不校验头/版本，打印 Version: 0.0 后在记录遍历里死循环
#    （实测：timeout 10 -> rc=124，stdout 87B，stderr 0B）。用 timeout 兜住再断言，
#    否则 CI 会被这个上游缺陷挂死。
if command -v timeout >/dev/null 2>&1; then
  printf 'not an index.dat file at all\n' > "$T/junk.dat"
  run junk 124 timeout 5 pasco "$T/junk.dat"
  has junk 'Version: 0.0'
  nohas junk 'not an index.dat file at all'
else
  echo "SKIP 非 index.dat 用例：环境无 timeout，无法兜住上游死循环"
fi

printf 'ASSERTIONS=%d PASS=%d FAIL=%d\n' "$assert" "$pass" "$fail"
[ "$fail" = 0 ] || exit 1
exit 0
