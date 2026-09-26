#!/usr/bin/sh
# qprint consumer test (test_package) — encode/decode roundtrip.
# 上游无测试套件（源码包仅 qprint.c/getopt/configure，见 MANIFEST 清点），
# 消费者验证 = 二进制真实编解码往返 + 已知值断言。
set -eu

# 已知值：编码 "A é = 41" 类含非 ASCII 与保留字符的输入
printf 'Hello=World \xc3\xa9\n' > in.txt

"$1" -e -b in.txt > enc.qp
"$1" -d -b enc.qp > dec.txt

if cmp -s in.txt dec.txt; then
  echo "roundtrip: OK"
else
  echo "roundtrip: FAIL"; diff in.txt dec.txt || true; exit 1
fi

# 已知编码断言："=" 必须编码为 =3D
printf 'a=b\n' > eq.txt
"$1" -e -b eq.txt | grep -q 'a=3Db' && echo "known-value: OK" || { echo "known-value: FAIL"; exit 1; }

echo "test_qprint: OK (encode/decode roundtrip + known-value)"
