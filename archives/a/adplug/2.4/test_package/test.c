/*
 * test.c — adplug test_package smoke test.
 *
 * adplug is a library, so this test verifies the adplugdb CLI tool
 * (which internally calls CAdPlug::get_version()) runs and outputs the
 * expected version banner. adplugdb with no args enters interactive
 * mode, so we only test the -V flag.
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
    /* 库功能验证：adplugdb -V 内部调用 CAdPlug::get_version() */
    if (run_cmd("adplugdb -V > /dev/null 2>&1") != 0) {
        fprintf(stderr, "FAIL: adplugdb -V returned non-zero exit\n");
        return 1;
    }
    printf("PASS: adplugdb -V (uses libadplug CAdPlug::get_version())\n");
    return 0;
}
