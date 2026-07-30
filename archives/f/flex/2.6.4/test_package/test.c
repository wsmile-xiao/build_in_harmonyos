/*
 * flex test_package — verify flex binary and libfl work correctly.
 *
 * This test:
 *   1. Runs `flex --version` to verify the binary is functional.
 *   2. Generates a simple scanner from an inline .l file.
 *   3. Compiles and links the generated scanner against libfl.
 *   4. Runs the scanner to verify it produces correct output.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

/* A minimal flex scanner that matches integers and prints them. */
static const char *LEX_CONTENT =
    "%{\n"
    "#include <stdio.h>\n"
    "%}\n"
    "%%\n"
    "[0-9]+  { printf(\"NUM:%s\\n\", yytext); }\n"
    "[ \\t]+ { /* skip whitespace */ }\n"
    ".       { /* skip other chars */ }\n"
    "%%\n"
    "int yywrap(void) { return 1; }\n"
    "int main(void) { yylex(); return 0; }\n";

static int write_file(const char *path, const char *content) {
    FILE *f = fopen(path, "w");
    if (!f) return -1;
    if (fputs(content, f) == EOF) {
        fclose(f);
        return -1;
    }
    fclose(f);
    return 0;
}

/* Run a command and return 0 on success, -1 on failure. */
static int run_cmd(const char *cmd) {
    int ret = system(cmd);
    if (ret == -1) return -1;
    return WIFEXITED(ret) && WEXITSTATUS(ret) == 0 ? 0 : -1;
}

static void cleanup(const char *lex, const char *cfile, const char *bin) {
    remove(lex);
    remove(cfile);
    remove(bin);
}

int main(void) {
    int ret;
    /* Use TMPDIR if set, otherwise fall back to current directory
     * (not /tmp, which may not exist or be HMDFS-incompatible). */
    const char *tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = ".";
    char lex_path[512], c_path[512], bin_path[512], cmd[4096];

    snprintf(lex_path, sizeof(lex_path), "%s/flex_test.l", tmpdir);
    snprintf(c_path,   sizeof(c_path),   "%s/flex_test.c", tmpdir);
    snprintf(bin_path, sizeof(bin_path), "%s/flex_test_bin", tmpdir);

    /* Test 1: flex --version */
    printf("Test 1: flex --version ... ");
    ret = run_cmd("flex --version");
    if (ret != 0) {
        printf("FAIL\n");
        cleanup(lex_path, c_path, bin_path);
        return 1;
    }
    printf("PASS\n");

    /* Test 2: generate scanner from .l file */
    printf("Test 2: flex generates scanner ... ");
    if (write_file(lex_path, LEX_CONTENT) != 0) {
        printf("FAIL (cannot write %s)\n", lex_path);
        cleanup(lex_path, c_path, bin_path);
        return 1;
    }
    snprintf(cmd, sizeof(cmd), "flex -o '%s' '%s'", c_path, lex_path);
    ret = run_cmd(cmd);
    if (ret != 0) {
        printf("FAIL\n");
        cleanup(lex_path, c_path, bin_path);
        return 1;
    }
    /* Verify the generated .c file exists and is non-empty */
    {
        FILE *f = fopen(c_path, "r");
        if (!f) {
            printf("FAIL (generated %s not found)\n", c_path);
            cleanup(lex_path, c_path, bin_path);
            return 1;
        }
        if (fseek(f, 0, SEEK_END) != 0) {
            printf("FAIL (seek failed on %s)\n", c_path);
            fclose(f);
            cleanup(lex_path, c_path, bin_path);
            return 1;
        }
        long sz = ftell(f);
        fclose(f);
        if (sz <= 0) {
            printf("FAIL (generated %s is empty)\n", c_path);
            cleanup(lex_path, c_path, bin_path);
            return 1;
        }
    }
    printf("PASS\n");

    /* Test 3: compile and link the generated scanner */
    printf("Test 3: compile scanner with libfl ... ");
    snprintf(cmd, sizeof(cmd), "${CC:-cc} -o '%s' '%s' 2>&1", bin_path, c_path);
    ret = run_cmd(cmd);
    if (ret != 0) {
        printf("FAIL\n");
        cleanup(lex_path, c_path, bin_path);
        return 1;
    }
    printf("PASS\n");

    /* Test 4: run the scanner and verify output */
    printf("Test 4: run scanner on '42 hello 7' ... ");
    char out_path[512];
    snprintf(out_path, sizeof(out_path), "%s/flex_test_out.txt", tmpdir);
    snprintf(cmd, sizeof(cmd), "echo '42 hello 7' | '%s' > '%s'", bin_path, out_path);
    ret = run_cmd(cmd);
    if (ret != 0) {
        printf("FAIL (scanner exit code %d)\n", ret);
        cleanup(lex_path, c_path, bin_path);
        remove(out_path);
        return 1;
    }
    /* Verify the output contains expected NUM: lines */
    {
        FILE *f = fopen(out_path, "r");
        if (!f) {
            printf("FAIL (cannot open %s)\n", out_path);
            cleanup(lex_path, c_path, bin_path);
            return 1;
        }
        char buf[256];
        int found_42 = 0, found_7 = 0;
        while (fgets(buf, sizeof(buf), f)) {
            if (strstr(buf, "NUM:42")) found_42 = 1;
            if (strstr(buf, "NUM:7"))  found_7 = 1;
        }
        fclose(f);
        remove(out_path);
        if (!found_42 || !found_7) {
            printf("FAIL (expected NUM:42 and NUM:7 in output)\n");
            cleanup(lex_path, c_path, bin_path);
            return 1;
        }
    }
    printf("PASS\n");

    /* Cleanup */
    cleanup(lex_path, c_path, bin_path);

    printf("All tests passed.\n");
    return 0;
}
