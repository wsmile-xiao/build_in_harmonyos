#!/usr/bin/env python3
"""Conan test_package for pytablewriter — R34 real API usage (no empty shell).

pytablewriter is pure Python. The verifiable artifact is the pytablewriter
package under <pkg>/lib/python3.12/site-packages/. This test actually imports
the packaged pytablewriter and writes a real table with a writer, then reads
back the output — proving the package is importable and functional, not just
present on disk.

pytablewriter depends on dataproperty/mbstrdecoder/pathvalidate/tabledata/
tcolorpy/typepy — each packaged into its own site-packages. argv[2:] carries
every dependency package folder so all site-packages get added to sys.path.
"""
import os
import sys


def _add_site_packages(folder):
    # 布局 A：lib/python3.12/site-packages（site-packages 层）
    for pyver in ("python3.12", "python3.11", "python3"):
        sp = os.path.join(folder, "lib", pyver, "site-packages")
        if os.path.isdir(sp):
            sys.path.insert(0, sp)
            return
    # 布局 B：lib/python3/<pkg>（无 site-packages 层，包直接挂在 python3/ 下）
    for pyver in ("python3.12", "python3.11", "python3"):
        lib = os.path.join(folder, "lib", pyver)
        if os.path.isdir(lib):
            sys.path.insert(0, lib)
            return
    # fallback: package may put files under lib/ directly
    lib = os.path.join(folder, "lib")
    if os.path.isdir(lib):
        sys.path.insert(0, lib)


def main():
    pkg = sys.argv[1]
    # packaged pytablewriter site-packages
    _add_site_packages(pkg)
    # all dependency package folders (argv[2:])
    for dep in sys.argv[2:]:
        _add_site_packages(dep)

    # R34: import the packaged module and call a real API.
    import pytablewriter

    ver = getattr(pytablewriter, "__version__", "?")
    if ver != "1.2.1":
        print(f"FAIL: pytablewriter.__version__ = {ver!r}, expected '1.2.1'",
              file=sys.stderr)
        return 1

    # Write a real Markdown table and assert the output contains expected rows.
    writer = pytablewriter.MarkdownTableWriter()
    writer.table_name = "test_table"
    writer.headers = ["col_a", "col_b"]
    writer.value_matrix = [["1", "abc"], ["2", "def"]]
    out = writer.dumps()
    # 断言基于内容包含（表格列对齐/填充宽度会随值变化，不写死精确空格）
    for expected in ("test_table", "col_a", "col_b", "abc", "def"):
        if expected not in out:
            print(f"FAIL: MarkdownTableWriter output missing {expected!r}:\n{out}",
                  file=sys.stderr)
            return 1

    print(f"OK: pytablewriter {ver} imported from package; "
          f"MarkdownTableWriter output:\n{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
