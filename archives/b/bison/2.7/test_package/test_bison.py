import pathlib
import shutil
import subprocess
import sys
import tempfile


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_bison.py BISON CLANG")

    bison = pathlib.Path(sys.argv[1])
    clang = pathlib.Path(sys.argv[2])
    if not bison.is_file() or not bison.stat().st_mode & 0o111:
        raise SystemExit(f"bison is not executable: {bison}")
    if not clang.is_file() or not clang.stat().st_mode & 0o111:
        raise SystemExit(f"clang is not executable: {clang}")

    version = run([str(bison), "--version"],
                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
    first_line = version.splitlines()[0] if version.splitlines() else ""
    if "bison (GNU Bison) 2.7" not in first_line:
        raise SystemExit(f"unexpected bison version: {first_line}")

    work = pathlib.Path(tempfile.mkdtemp(prefix="bison-test-"))
    try:
        grammar = work / "calc.y"
        generated = work / "calc.c"
        binary = work / "calc"
        grammar.write_text(
            "%{\n"
            "#include <stdio.h>\n"
            "int yylex(void);\n"
            "void yyerror(const char *message) { (void)message; }\n"
            "%}\n"
            "%token NUMBER\n"
            "%%\n"
            "input: NUMBER { if ($1 == 42) puts(\"parser assertion passed\"); };\n"
            "%%\n"
            "int yylex(void) { static int state; if (state++) return 0; "
            "yylval = 42; return NUMBER; }\n"
            "int main(void) { return yyparse(); }\n",
            encoding="utf-8",
        )
        run([str(bison), "-o", str(generated), str(grammar)])
        run([str(clang), f"-I{work}", str(generated), "-o", str(binary)])
        result = run([str(binary)], stdout=subprocess.PIPE).stdout
        if "parser assertion passed" not in result:
            raise SystemExit(f"unexpected parser output: {result!r}")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    print("=== bison tests PASSED ===")


if __name__ == "__main__":
    main()
