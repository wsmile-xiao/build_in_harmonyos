#!/usr/bin/env python3
"""pari-galpol 上游功能测试入口（galoisgetpol）用例生成器.

为什么需要生成器：gp 2.17.4 的这构建里 **没有** 文件系统探测原语
（`file_exists` / `is_file` / `is_dir` / `wildcards` 一律
`*** not a function in function call`，实测见 notes.md 踩坑表），
自枚举版驱动写不出来。因此由本脚本**枚举被测数据树**、生成一张
纯 straight-line 的 .gp 断言脚本，再交给已发布的 gp 执行——
用例集合完全由被测目录决定（不硬编码条目清单），gp 侧只做真实的
`galoisgetpol(n,k,flag)` 读取与相等比较。

用法:
    python3 upstream-gp-sweep-generator.py <datadir_root> > sweep.gp
        <datadir_root> = 含 galpol/ 的根，本包为 <pkg>/res/pari
    gp-2.17 -f -q -s 500000000 < sweep.gp

用例（对包内全部条目，非抽样，逐条 name|PASS/FAIL）:
    nb_count_<n>                <n>/nb 的值 == 该阶下组目录数      ×143
    roundtrip_real_<n>_<k>      galoisgetpol(n,k,1) == read(<n>/<k>/real)
                                且 poldegree(返回多项式) == n        ×3657
    roundtrip_complex_<n>_<k>   galoisgetpol(n,k,2) == read(<n>/<k>/complex)
                                且 poldegree(返回多项式) == n        ×3537
"""
import os
import sys

HDR = '''default(datadir, "@@ROOT@@");
dd = default(datadir);
np = 0; nf = 0;
rchk(nm, ok) = {
  if(ok, np = np + 1, nf = nf + 1);
  print(Str(nm, "|", if(ok, "PASS", "FAIL")));
};
ck(n, k, f, rel) = {
  my(a, b, ok);
  a = read(Str(dd, "/", rel));
  b = galoisgetpol(n, k, f);
  ok = (a == b) && (poldegree(b[1]) == n);
  if(f == 1, rchk(Str("roundtrip_real_", n, "_", k), ok), rchk(Str("roundtrip_complex_", n, "_", k), ok));
};
nbchk(n, e) = {
  my(v, ok);
  v = readvec(Str(dd, "/galpol/", n, "/nb"))[1];
  ok = (v == e);
  rchk(Str("nb_count_", n), ok);
};
'''


def main(root):
    base = os.path.join(root, "galpol")
    if not os.path.isdir(base):
        sys.exit("no galpol/ under %s" % root)
    out = [HDR.replace("@@ROOT@@", root)]
    orders = sorted(int(d) for d in os.listdir(base) if d.isdigit())
    nreal = ncplx = 0
    for n in orders:
        p = os.path.join(base, str(n))
        ks = sorted((int(d) for d in os.listdir(p) if d.isdigit()), key=int)
        out.append("nbchk(%d, %d);" % (n, len(ks)))
        for k in ks:
            if os.path.isfile(os.path.join(p, str(k), "real")):
                out.append('ck(%d, %d, 1, "galpol/%d/%d/real");' % (n, k, n, k))
                nreal += 1
            if os.path.isfile(os.path.join(p, str(k), "complex")):
                out.append('ck(%d, %d, 2, "galpol/%d/%d/complex");' % (n, k, n, k))
                ncplx += 1
    out.append('print(Str("SUMMARY pass=", np, " fail=", nf, " total=", np + nf));')
    sys.stdout.write("\n".join(out) + "\n")
    sys.stderr.write("orders=%d real=%d complex=%d cases=%d\n"
                     % (len(orders), nreal, ncplx, len(orders) + nreal + ncplx))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: %s <datadir_root>" % sys.argv[0])
    main(sys.argv[1])
