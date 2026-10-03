/* test_pdlua — smoke test for the pdlua.pd_linux Pd external.
 *
 * A Pd external is a shared object that is dlopen'ed by the Pd host, which
 * supplies the Pure Data API symbols it references (binbuf_*, class_new,
 * freebytes, ...). It therefore cannot be dlopen'ed by a standalone
 * process. This test instead drives the real Pd binary (from the puredata
 * dependency) the way a user would, and verifies the pdlua loader:
 *   1. `pd -lib pdlua` boots and reports the pdlua banner + Lua version.
 *   2. a `.pd_lua` external (hello) is instantiated through the loader and
 *      actually executes (prints "Hello ..."); `-send "pd quit"` is
 *      processed by Pd after the patch loads, so the run terminates.
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* run a shell command, return 1 if its combined output contains `needle` */
static int run_and_grep(const char *cmd, const char *needle)
{
    char buf[4096];
    int found = 0;
    FILE *fp = popen(cmd, "r");
    if (!fp)
        return -1;
    while (fgets(buf, sizeof buf, fp)) {
        if (strstr(buf, needle))
            found = 1;
    }
    pclose(fp);
    return found;
}

int main(int argc, char **argv)
{
    if (argc < 3) {
        fprintf(stderr, "usage: %s <pd-binary> <pdlua-install-dir>\n", argv[0]);
        return 2;
    }
    const char *pd_bin = argv[1];
    const char *dir = argv[2];
    char cmd[8192];
    int rc = 0;

    /* [1] boot headless Pd and load the pdlua library.
     * Grep the loader banner ("... Using lua version 5.4") rather than the
     * bare string "pdlua": a failed dlopen also mentions "pdlua" in Pd's
     * error message (e.g. "pdlua: can't load library"), which would make a
     * loose match pass the check even when loading actually failed. */
    snprintf(cmd, sizeof cmd,
             "\"%s\" -batch -nogui -nrt -path \"%s\" -lib pdlua -send \"pd quit\" 2>&1",
             pd_bin, dir);
    if (run_and_grep(cmd, "Using lua version") > 0)
        printf("OK: pdlua library loaded by pd\n");
    else {
        fprintf(stderr, "FAIL: pd did not report loading pdlua\n");
        rc = 1;
    }

    /* [2] instantiate hello.pd_lua through the pdlua loader.
     * The generated patch is written to a pid-suffixed temp file and
     * removed afterwards, so concurrent runs do not collide and no
     * artifact is left behind in the build directory. */
    snprintf(cmd, sizeof cmd,
             "tmp=_pdlua_hello_$$.pd; "
             "printf '#N canvas 0 0 200 100 10;\\n#X obj 10 10 hello;\\n' > \"$tmp\"; "
             "\"%s\" -batch -nogui -nrt -lib pdlua -path \"%s\" -path \"%s/pdlua\" "
             "-path \"%s/pdlua/examples\" -send \"pd quit\" \"$tmp\" 2>&1; "
             "rc=$?; rm -f \"$tmp\"; exit $rc",
             pd_bin, dir, dir, dir);
    if (run_and_grep(cmd, "Hello") > 0)
        printf("OK: hello.pd_lua instantiated through the pdlua loader\n");
    else {
        fprintf(stderr, "FAIL: hello.pd_lua did not execute inside pd\n");
        rc = 1;
    }
    return rc;
}
