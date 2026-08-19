#!/usr/bin/env python3
"""test_namespacesupport.py — 独立测试源（L0c 要求 test_package/ 有 .c/.cpp/.py
测试文件，conanfile.py 内联断言不算）。

REAL check: perl 加载打包的 XML::NamespaceSupport 模块并做最小 API 调用
（start_element/end_element namespace 栈行为），断言模块可被 @INC 解析。
Usage: test_namespacesupport.py <site-perl-dir>
"""
import os
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_namespacesupport.py <site-perl-dir>")
    site = sys.argv[1]
    # perl 包带版本层路径（site_perl/5.42.0/XML/NamespaceSupport.pm）——
    # 固定路径检查会漏，用 os.walk 递归定位；perl 调用时 PERL5LIB 传 site 根
    found = False
    if os.path.isdir(site):
        for root, _dirs, files in os.walk(site):
            if "NamespaceSupport.pm" in files and os.path.basename(root) == "XML":
                found = True
                break
    if not found:
        raise AssertionError(f"XML/NamespaceSupport.pm missing under {site}")
    # 真实 API 检查：构造 NamespaceSupport，push/pop context，
    # 断言 get_prefixes 返回元素栈上的命名空间前缀
    perl_code = (
        "use XML::NamespaceSupport;"
        "my $ns = XML::NamespaceSupport->new();"
        "$ns->push_context();"
        "$ns->declare_prefix('x', 'http://example.com/');"
        "my @p = $ns->get_prefixes();"
        "die 'prefix missing' unless grep { $_ eq 'x' } @p;"
        "$ns->pop_context();"
        "print qq(OK: XML::NamespaceSupport API ok\\n);"
    )
    env = dict(os.environ)
    env["PERL5LIB"] = ":".join(x for x in (site, env.get("PERL5LIB", "")) if x)
    r = subprocess.run(["/data/service/hnp/bin/perl", "-e", perl_code],
                       capture_output=True, text=True, env=env)
    if r.stdout:
        sys.stdout.write(r.stdout)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        raise SystemExit(f"perl XML::NamespaceSupport check failed (rc={r.returncode})")
    print("OK: perl-xml-namespacesupport 1.12 consumer check")


if __name__ == "__main__":
    main()
