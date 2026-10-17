"""kb_taxonomy — 知识图谱 category 受控词表与归一化（v12.4）

设计（借鉴 OpenViking merge_op 语义，纯规则零 LLM）:
- CORE_VOCAB: 高频核心原子词（~45，按域分组）
- ALIASES:    明确同义词 → 词表词映射
- 拆分规则:   前缀复合词（platform-x / libc-x / musl-x / ohos-x / conan-x ...）递归拆分;
              a-b 若 a/b 均为已知词则拆为两词
- 长尾词:     归一格式（小写/连字符/去引号）后保留，validate 给 warning（不阻塞），
              由 add/promote 写入关口渐进收敛
- 写入关口:   cmd_promote / graph add 时自动归一 —— promote 决策权仍在人工审核，
              归一化只统一表达形式，不改变知识内容
"""

from __future__ import annotations

# ── 受控词表（原子词，按域分组; 排序输出时按此表顺序稳定排列）──
CORE_VOCAB: list[str] = [
    # 平台域
    "platform", "compat", "limitation", "detection", "hmdfs", "ohos",
    "selinux", "kernel", "portability",
    # libc 域
    "libc", "musl", "posix", "syscall", "headers", "threading", "socket", "network",
    # 构建系统域
    "build-system", "cmake", "autotools", "meson", "make", "configure", "qmake",
    # 工具链/编译域
    "toolchain", "compiler", "clang", "llvm", "linking", "asm", "c++", "cross-compile", "warnings",
    # 语言生态
    "python", "rust", "go", "perl", "java", "lua", "fortran",
    # 包管理/依赖
    "conan", "dependency", "pkg-config", "packaging", "version",
    # 阶段域
    "compilation", "install", "runtime", "testing", "patch",
    # 其他高频
    "environment", "filesystem", "permissions", "security", "nls",
    "shell", "gnulib", "libtool",
    "symlink", "static-library", "relocatable", "api", "memory", "architecture",
]

_VOCAB_SET = set(CORE_VOCAB)

# ── 别名映射（归一到词表词; 值为词表词或空格分隔多词）──
ALIASES: dict[str, str] = {
    # 平台同义
    "harmonyos": "ohos",
    "config": "configure",
    "warning": "warnings",
    "cross": "cross-compile",
    "cross-compilation": "cross-compile",
    "cross-build": "cross-compile",
    "compile": "compilation",
    "porting": "portability",
    "adaptation": "portability",
    "sdk": "ohos toolchain",
    "upstream-test-compatibility": "testing compat",
    "compatibility": "compat",
    "compatible": "compat",
    "tool-compat": "compat toolchain",
    "shell-compat": "compat shell",
    "posix-compatibility": "posix compat",
    "api-compatibility": "api compat",
    "build-system-compatibility": "build-system compat",
    "platform-compatibility": "platform compat",
    "ohos-porting": "ohos portability",
    "platform-adaptation": "platform portability",
    "patch-portability": "patch portability",
    "platform-restriction": "platform limitation",
    "restriction": "limitation",
    "testing-limitation": "testing limitation",
    "runtime-capability": "runtime detection",
    "feature-detection": "detection",
    "platform-diff": "platform",
    "platform-success": "platform",
    # 构建工具
    "build-tool": "build-system",
    "build-tools": "build-system",
    "build-tool-missing": "toolchain",
    "tool-missing": "toolchain",
    "toolchain-missing-sign-tool": "toolchain",
    "autotools-config": "autotools configure",
    "autotools-bootstrap": "autotools",
    "autotools-triplet": "autotools cross-compile",
    "bootstrap": "autotools",
    "configuration": "configure",
    "custom-configure": "configure",
    "custom-makefile": "make",
    "makefile": "make",
    "cmake-modules-missing": "cmake",
    "cmake-packaging": "cmake packaging",
    "cmake-exports": "cmake",
    "cmake-template": "cmake",
    "cmake-cross-compile": "cmake cross-compile",
    "build-system-qmake": "qmake",
    "cmakedeps": "conan cmake",
    # 编译/链接
    "compiler-warning": "warnings",
    "diagnostics": "warnings",
    "static-linking": "linking",
    "dynamic-linking": "linking",
    "runtime-linking": "runtime linking",  # 拆分规则也会处理, 此处兜底
    "linker": "linking",
    "soname": "linking",
    "linker-dependency": "linking dependency",
    "rpath": "linking",
    "relocation": "relocatable",
    "relocatable-package": "relocatable",

    "embedded-compiler": "compiler",
    "rust-toolchain": "rust toolchain",
    "old-code-cpp17": "c++",
    "c-api": "api",
    "api-missing": "api",
    "missing-function": "api",
    "api-difference": "api platform",
    "platform-api-capability-split": "platform api",
    # libc
    "libc-runtime-capability-detection": "libc detection",
    "ohos-musl-libc-header": "musl headers",
    "musl-compat": "musl compat",
    "libc-compat": "libc compat",
    "gnu": "libc",
    "gnulib": "gnulib",  # 保留专名
    "threads": "threading",
    "time-functions": "libc",
    "mmap": "libc syscall",
    "setitimer": "syscall",
    "signal": "syscall",
    "poll": "socket",
    "epoll": "socket",
    "entropy": "libc",
    "fmemopen": "libc",
    "seccomp": "syscall security",
    "toybox": "ohos",
    "zoneinfo": "nls",
    "timezone": "nls",
    "tzcode": "nls",
    "tzdir": "nls",
    "iana": "nls",
    "gettext": "nls",
    # 包管理/依赖
    "conan-recipe": "conan",
    "conan-release": "conan",
    "conan-package-model": "conan",
    "conan-source-folder-isolation": "conan",
    "conan-multi-case-failure-aggregation": "conan",
    "conan-test-execution": "conan testing",
    "conan-source-acquisition": "conan",
    "conan-cmake-dependency-bridge": "conan cmake",
    "conan-cmake-test-argument-routing": "conan cmake testing",
    "circular-dependency": "dependency",
    "dependency-handling": "dependency",
    "dependency-management": "dependency",
    "dependency-discovery": "dependency",
    "dependency-missing": "dependency",
    "dependency-library": "dependency",
    "vendored-deps": "dependency",
    "version-mismatch": "version",
    "version-conflict": "version",
    "pkgconfig": "pkg-config",
    "precompiled-package": "packaging",
    "source-package": "packaging",
    "source-distribution": "packaging",
    "source-packaging": "packaging",
    "runtime-packaging": "runtime packaging",
    "installed-layout": "packaging",

    "package-discovery": "packaging",
    "pip-wheel": "python packaging",
    "site-packages": "python",
    "luarocks": "lua packaging",
    "perl-xs": "perl",
    "xs": "perl",
    "ctypes": "python",
    "nltk": "python",
    "jvm": "java",
    "jni": "java",
    "native-image": "java",
    "noarch": "packaging",
    "test-package": "testing packaging",
    # 安全
    "crypto": "security",
    "ssl": "security",
    "openssl": "security",
    "elf-signing": "security linking",
    "platform-elf-signature": "security",
    "signing": "security",
    "harmonyos-security": "ohos security",
    "toctou": "security",
    "secure-temporary-directory": "security environment",
    "source-integrity": "security",
    # 环境/路径
    "build-environment": "environment",
    "env": "environment",
    "paths": "environment",
    "header-path": "headers",
    "header-search": "headers",
    "header": "headers",
    "missing-header": "headers",
    "generated-header": "headers",
    "header-only": "headers",
    "platform-headers": "headers",
    "kernel-headers": "kernel headers",
    "ohos-sdk": "ohos toolchain",
    "ohos-sdk-gap": "ohos toolchain",
    "sdk-conflict": "toolchain",
    "ohos-toolchain-migration": "ohos toolchain",
    "toolchain-llvm-plugin": "toolchain llvm",

    "hmmac": "ohos toolchain",

    "subprocess": "shell",
    "command": "shell",
    "scripts": "shell",
    "sed": "shell",
    # 杂项高频
    "tools": "toolchain",
    "tool": "toolchain",
    "resolved": "",           # 无信息量
    "blocking": "",
    "ci": "",
    "build": "build-system",
    "build-pattern": "build-system",
    "build-parameters": "build-system",
    "generated-config": "configure",
    "windows": "platform",

    "allocator": "memory",
    "null-pointer": "memory",
    "concurrency": "threading",
    "thread-lifecycle": "threading",
    "resource-lifetime": "runtime",
    "finalizer": "runtime",
    "rollback": "runtime",
    "transaction": "runtime",
    "scratch": "runtime",
    "fallback": "runtime",
    "runtime-behavior": "runtime",
    "runtime-probe": "runtime detection",
    "runtime-feature-detection": "runtime detection",
    "namespace": "runtime",
    "extension": "runtime",
    "macro": "runtime",
    "constant": "runtime",
    "variable-undefined": "runtime",
    "assert": "testing",
    "ndebug": "testing",
    "coverage": "testing",
    "test-structure": "testing",
    "test-helper": "testing",
    "test-evidence-provenance": "testing",
    "testing-alternative": "testing",
    "upstream-test-framework-migration": "testing",
    "ohos-upstream-test-compatibility": "ohos testing compat",
    "lit-testsuite": "testing llvm",
    "fuzz-corpus-runner": "testing",
    "upstream-latent-bug": "testing",
    "validation-methodology": "testing",
    "missing-file": "filesystem",
    "file-layout": "filesystem",
    "path-policy": "filesystem permissions",
    "filesystem-hmdfs": "filesystem hmdfs",
    "multi-source": "filesystem",
    "permission": "permissions",
    "go-link-permission": "go linking permissions",
    "network-restricted": "network",
    "multi-source-download": "network",

    "patch-quality": "patch",
    "patch-pipeline": "patch",
    "patch-routing": "patch",
    "ci-binary-patch-failure": "patch",
    "autotools-patch-compatibility": "patch autotools compat",
    "autotools-generated-doc-install": "autotools install",
    "autotools-static-pic-contract": "autotools linking",
    "unified-diff-context-whitespace": "patch",
    "python-popen-text-decoding": "python",
    "encoding": "python",
    "man": "packaging",
    "post-processing": "packaging",
    "external-assets": "packaging",
    "resource-data": "packaging",
    "data-package-adaptation": "packaging",
    "resource-package-adaptation": "packaging",
    "nlp-dictionary-adaptation": "packaging",
    "ohos-font-resource-package-methodology": "ohos packaging",
    "static-package-registration": "packaging",
    "manifest-yaml": "packaging",
    "target-graph": "packaging",
    "consumer-contract": "api",
    "package-contract": "api packaging",
    "error-contract": "api",
    "contract": "api",
    "public-api": "api",
    "system-interface": "api",
    "system-service": "api",
    "generator-api": "api",
    "protocol-data": "api",
    "audio-backend-porting": "portability",
    "tablegen": "llvm",
    "fortran-module-abi-contract": "fortran linking",
    "c99": "libc",
    "c-ownership-uninitialized-state": "memory",
    "cpp-polar-negative-radius": "c++",
    "native-crash": "runtime",
    "ai-mistake": "runtime",
    "icu": "dependency",
    "openblas": "dependency",
    "fftw-runtime-planning": "runtime dependency",
    "postgresql": "dependency",
    "fbida": "",
    "l2": "",
    "param": "",
    "native": "runtime",
}

# ── 拆分前缀（复合词递归拆分）──
_SPLIT_PREFIXES = (
    "platform", "ohos", "harmonyos", "libc", "musl", "posix", "conan",
    "cmake", "autotools", "python", "rust", "perl", "java", "ohos-sdk",
    "kernel", "static", "cross", "compiler", "toolchain",
)

_MAX_TOKENS = 5  # 归一后每条 category 的最大词数

def _split_compound(tok: str) -> list[str]:
    """递归拆分前缀复合词; a-b 两部分均为已知词时也拆。词表词不拆。"""
    if tok in _VOCAB_SET:
        return [tok]
    for p in _SPLIT_PREFIXES:
        if tok != p and tok.startswith(p + "-"):
            rest = tok[len(p) + 1:]
            return [_alias_one(p)] + _split_compound(rest)
    if "-" in tok:
        a, _, b = tok.rpartition("-")
        if a in _VOCAB_SET and b in _VOCAB_SET:
            return [a, b]
    return [tok]

def _alias_one(tok: str) -> str:
    return ALIASES.get(tok, tok)

def _expand_token(tok: str) -> list[str]:
    """别名优先于拆分: 整词命中别名 → 对映射结果逐词展开; 否则拆分复合词后逐词再查别名。"""
    aliased = ALIASES.get(tok)
    if aliased is not None:
        out: list[str] = []
        for w in aliased.split():
            if not w:
                continue
            if w == tok:          # 环保护: 自映射/互指
                out.append(w)
            else:
                out.extend(_expand_token(w))
        return out
    out = []
    for sub in _split_compound(tok):
        if sub != tok:
            out.extend(_expand_token(sub))
        else:
            mapped = ALIASES.get(sub)
            out.extend(mapped.split() if mapped else [sub])
    return out

def normalize_category(raw: str) -> tuple[str, list[str]]:
    """归一化 category 字符串。

    Returns:
        (normalized, unknown_tokens)
        normalized: 逗号+空格分隔的受控词（按 CORE_VOCAB 声明序稳定排列, 上限 5 词）
        unknown_tokens: 无法映射到词表的长尾词（保留在结果中, 供 lint 告警）
    """
    if not raw or not raw.strip():
        return "", []
    toks: list[str] = []
    for piece in raw.replace('"', " ").replace(";", ",").split("|"):
        for t in piece.split(","):
            t = t.strip().lower().replace("_", "-").replace(" ", "-")
            if not t:
                continue
            for sub in _expand_token(t):
                if sub and sub not in toks:
                    toks.append(sub)
    unknown = [t for t in toks if t not in _VOCAB_SET]
    # 稳定排序: 词表声明序优先, 长尾词按字母序垫后
    order = {w: i for i, w in enumerate(CORE_VOCAB)}
    toks.sort(key=lambda t: (order.get(t, len(order)), t))
    return ", ".join(toks[:_MAX_TOKENS]), unknown

def lint_category(raw: str) -> list[str]:
    """返回 category 中不在受控词表的 token（供 validate 告警）。"""
    _, unknown = normalize_category(raw)
    return unknown

# ── CLI: python3 -m ohc kb_taxonomy [--dry-run] ── (主要供迁移脚本与测试使用)

def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="kb-taxonomy", description="category 受控词表工具")
    parser.add_argument("query", nargs="?", help="测试归一化: 传入原始 category 字符串")
    args = parser.parse_args(argv)
    if args.query:
        norm, unknown = normalize_category(args.query)
        print(f"归一化: {norm}")
        if unknown:
            print(f"长尾词(保留): {', '.join(unknown)}")
        return 0
    print(f"受控词表 ({len(CORE_VOCAB)} 词): {', '.join(CORE_VOCAB)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
