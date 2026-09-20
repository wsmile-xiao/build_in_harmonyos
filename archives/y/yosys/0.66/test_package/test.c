/*
 * test.c — yosys test_package smoke test.
 *
 * yosys is a command-line RTL synthesis tool (not a library), so this test
 * executes the installed binary through popen():
 *   1. `yosys -V`  — the version banner must report 0.66
 *   2. a real synthesis of test.v (`read_verilog; synth; stat`) — this drives
 *      the parser, the pass pipeline, techmapping and the external ABC binary
 *      wired in via ABCEXTERNAL / ABC.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Run `cmd`, capture all of its stdout, and require `expect` to appear in it.
 * The output is collected into a growing buffer because a yosys synthesis log
 * is far larger than any fixed-size buffer worth putting on the stack. */
static int run(const char *cmd, const char *expect)
{
    FILE *p;
    char chunk[4096];
    size_t n, cap = 65536, len = 0;
    char *out;
    int found = 0, status;

    out = (char *)malloc(cap);
    if (!out) {
        fprintf(stderr, "FAIL: out of memory\n");
        return 1;
    }
    out[0] = '\0';

    p = popen(cmd, "r");
    if (!p) {
        fprintf(stderr, "FAIL: cannot run: %s\n", cmd);
        free(out);
        return 1;
    }
    while ((n = fread(chunk, 1, sizeof(chunk), p)) > 0) {
        if (len + n + 1 > cap) {
            char *grown;
            cap *= 2;
            grown = (char *)realloc(out, cap);
            if (!grown) {
                fprintf(stderr, "FAIL: out of memory\n");
                pclose(p);
                free(out);
                return 1;
            }
            out = grown;
        }
        memcpy(out + len, chunk, n);
        len += n;
        out[len] = '\0';
        if (!found && strstr(out, expect) != NULL)
            found = 1;
    }
    status = pclose(p);

    if (status != 0) {
        fprintf(stderr, "FAIL: non-zero exit from: %s\n--- output tail ---\n%s\n",
                cmd, len > 2000 ? out + len - 2000 : out);
        free(out);
        return 1;
    }
    if (!found) {
        fprintf(stderr, "FAIL: '%s' not found in output of: %s\n--- output tail ---\n%s\n",
                expect, cmd, len > 2000 ? out + len - 2000 : out);
        free(out);
        return 1;
    }
    free(out);
    return 0;
}

int main(void)
{
    if (run("yosys -V 2>&1", "Yosys 0.66"))
        return 1;
    printf("PASS: yosys -V reports the 0.66 version banner\n");

    /* "End of script." is printed only when the whole -p script ran to
     * completion; a failing abc would abort earlier with a non-zero exit. */
    if (run("yosys -p 'read_verilog test.v; synth -top top; stat' 2>&1",
            "End of script."))
        return 1;
    printf("PASS: synthesized test.v (read_verilog + synth + stat)\n");

    return 0;
}
