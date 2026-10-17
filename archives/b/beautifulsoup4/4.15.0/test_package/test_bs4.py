#!/usr/bin/env python3
"""beautifulsoup4 consumer test (R34): real API usage — HTML parsing."""
import sys


def main() -> int:
    import bs4

    if bs4.__version__ != "4.15.0":
        print(f"FAIL: bs4 version {bs4.__version__}", file=sys.stderr)
        return 1
    # 真实 API：BeautifulSoup 解析 HTML（html.parser 内置解析器——
    # bs4 import 链含 soupsieve/typing-extensions——真实运行）
    soup = bs4.BeautifulSoup("<p>hello</p>", "html.parser")
    text = soup.p.get_text()
    if text != "hello":
        print(f"FAIL: parse result {text!r}", file=sys.stderr)
        return 1
    print("OK: bs4 4.15.0 html parse ok (soupsieve/typing-extensions "
          "dependency linked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
