/*
 * test.c — aconf test_package smoke test.
 *
 * aconf is a Lua/shell daemon package (aconfd), not a C library. The
 * OHOS lua package does not ship a CLI interpreter, so this test verifies
 * the aconfd launcher is on PATH and executable, and that the core Lua
 * module file exists in the expected lua/5.4 path (passed via env var).
 *
 * NOTE: POSIX `test -x NAME` checks the CWD, NOT PATH — so we use
 * `command -v` to resolve the binary through PATH instead.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

static int run_cmd(const char *cmd) {
    int ret = system(cmd);
    if (ret == -1) return -1;
    return WIFEXITED(ret) && WEXITSTATUS(ret) == 0 ? 0 : -1;
}

int main(void) {
    const char *lua_dir = getenv("ACONF_LUA_DIR");
    char cmd[1024];

    /* 1. aconfd 在 PATH 中且可执行（command -v 搜索 PATH） */
    if (run_cmd("command -v aconfd > /dev/null 2>&1") != 0) {
        fprintf(stderr, "FAIL: aconfd not found on PATH\n");
        return 1;
    }
    printf("PASS: aconfd found on PATH\n");

    /* 2. 核心 Lua 模块存在（lua/5.4 路径，制品仓 lua 为 5.4.8） */
    if (!lua_dir) {
        fprintf(stderr, "FAIL: ACONF_LUA_DIR not set\n");
        return 1;
    }
    snprintf(cmd, sizeof(cmd), "test -f '%s/init.lua'", lua_dir);
    if (run_cmd(cmd) != 0) {
        fprintf(stderr, "FAIL: aconf/init.lua not present in %s\n", lua_dir);
        return 1;
    }
    printf("PASS: aconf/init.lua present (lua/5.4 path)\n");
    return 0;
}
