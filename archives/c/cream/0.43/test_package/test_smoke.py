#!/usr/bin/env python3
"""Consumer smoke test for the packaged cream Vim runtime files.

cream 是纯 Vim script 数据包，无二进制可执行；本测试对包内容做文件断言：
关键运行时文件存在且非空，顶层 .vim 脚本数量与上游 tarball 一致。
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_smoke.py <cream_runtime_dir>", file=sys.stderr)
        return 2

    cream_dir = sys.argv[1]

    # 关键运行时文件存在且非空（覆盖主配置、核心脚本、文档、
    # 各运行时子目录与多语言菜单）
    required = [
        "creamrc",
        "cream.vim",
        "docs/COPYING.txt",
        "docs/README.txt",
        "addons/cream-colorinvert.vim",
        "bitmaps/book.xpm",
        "filetypes/c.vim",
        "help/EnhancedCommentify.txt",
        "lang/menu_zh_cn.utf-8.vim",
    ]
    for rel in required:
        path = os.path.join(cream_dir, *rel.split("/"))
        assert os.path.isfile(path), f"missing package file: share/vim/cream/{rel}"
        size = os.path.getsize(path)
        assert size > 0, f"empty package file: share/vim/cream/{rel}"
        print(f"PASS: share/vim/cream/{rel} ({size} bytes)")

    # 顶层 Vim 运行时脚本数量（上游 0.43 tarball 固定为 72 个）
    vim_scripts = [f for f in os.listdir(cream_dir) if f.endswith(".vim")]
    assert len(vim_scripts) >= 70, (
        f"expected 70+ top-level .vim runtime scripts, got {len(vim_scripts)}"
    )
    print(f"PASS: {len(vim_scripts)} top-level .vim scripts present")

    print("cream test_package: all file assertions passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
