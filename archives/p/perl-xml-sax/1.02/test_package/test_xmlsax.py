#!/usr/bin/env python3
"""test_xmlsax.py — 独立测试源（L0c 要求 test_package/ 有 .c/.cpp/.py
测试文件，conanfile.py 内联断言不算）。

REAL check: perl 加载打包的 XML::SAX::Exception 模块并构造异常对象，
断言编译期 use 链（XML::SAX::Base/Exception）在打包后仍可解析。
Usage: test_xmlsax.py <site-perl-dirs...>（冒号分隔）
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_xmlsax.py <site-perl-dirs...>")
    sites = sys.argv[1].split(":")
    # 至少一个 site 含 XML/SAX/Exception.pm（perl 包带版本层路径
    # site_perl/5.42.0/XML/SAX/Exception.pm——固定路径检查会漏，
    # 用 os.walk 递归定位；perl 调用时 PERL5LIB 传 site 根即可）
    found = False
    for site in sites:
        if not os.path.isdir(site):
            continue
        for root, _dirs, files in os.walk(site):
            if "Exception.pm" in files and os.path.basename(root) == "SAX":
                found = True
                break
        if found:
            break
    if not found:
        raise AssertionError(f"XML/SAX/Exception.pm missing in given sites: {sites}")
    # 真实 API 检查：加载 XML::SAX::Exception 并构造 Parse 异常
    perl_code = (
        "use XML::SAX::Exception;"
        "my $e = XML::SAX::Exception::Parse->new(Message => 'x');"
        "die 'exception missing' unless $e && $e->{Message} eq 'x';"
        "print qq(OK: XML::SAX::Exception API ok\\n);"
    )
    env = dict(os.environ)
    env["PERL5LIB"] = ":".join(x for x in sites + [env.get("PERL5LIB", "")] if x)
    r = subprocess.run(["/data/service/hnp/bin/perl", "-e", perl_code],
                       capture_output=True, text=True, env=env)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"perl XML::SAX::Exception check failed (rc={r.returncode})")
    print("OK: perl-xml-sax 1.02 consumer check")


if __name__ == "__main__":
    main()
