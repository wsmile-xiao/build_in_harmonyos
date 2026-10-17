#!/usr/bin/env python3
"""Generate kazmath's upstream C++ test entry point without Python 2."""
import re
import sys
from pathlib import Path


def main():
    tests_dir = Path(sys.argv[1])
    output = tests_dir / "main.cpp"
    classes = []
    for path in sorted(tests_dir.glob("test_*.h")):
        text = path.read_text()
        match = re.search(r"class\s+(\w+)\s*:\s*public\s+TestCase\s*\{(.*?)\n\};", text, re.S)
        if not match:
            continue
        methods = re.findall(r"\bvoid\s+(test_\w+)\s*\(\s*\)", match.group(2))
        classes.append((path.name, match.group(1), methods))

    lines = [
        '#include <functional>',
        '#include <memory>',
        '#include "kaztest/kaztest.h"',
    ]
    lines.extend(f'#include "{name}"' for name, _, _ in classes)
    lines.extend(["", "int main(int argc, char* argv[]) {", "    std::shared_ptr<TestRunner> runner(new TestRunner());", "    std::string test_case;", "    if (argc > 1) test_case = argv[1];"])
    for _, cls, methods in classes:
        refs = ", ".join(f"&{cls}::{method}" for method in methods)
        names = ", ".join(f'"{cls}::{method}"' for method in methods)
        lines.extend([
            f"    runner->register_case<{cls}>(",
            f"        std::vector<void ({cls}::*)()>({{{refs}}}),",
            f"        {{{names}}});",
        ])
    lines.extend(["    return runner->run(test_case);", "}", ""])
    output.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
