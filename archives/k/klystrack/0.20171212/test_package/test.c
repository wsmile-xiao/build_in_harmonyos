/* klystrack 0.20171212 consumer test
 * 验证 klystrack 二进制 + SDL2 运行时可用：
 *   - 交叉编译场景（cross_building=true）：仅验证 SDL2 链接 + 头可用，跳过二进制运行
 *   - 本地场景（cross_building=false）：跑 klystrack --version/--help 验证二进制 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <SDL2/SDL.h>
#include <sys/wait.h>

int main(void) {
    /* 1. SDL_Init/SDL_Quit 验证 SDL2 运行时可用（SDL_INIT_EVENTS 避无头 CI 依赖） */
    if (SDL_Init(SDL_INIT_EVENTS) != 0) {
        fprintf(stderr, "FAIL: SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }
    SDL_Quit();
    printf("SDL2 runtime OK\n");

    /* 2. klystrack --version 输出非空（交叉编译场景 CI worker 跑不了 arm64 二进制 →
     *    跳过运行时验证，仅 SDL2 链接验证即通过）
     *    CI 真根因: arm64 二进制在 x64 host popen 跑炸 SIGSEGV exit 139
     *    修法: cross_building 时 Conan 传 SKIP_RUNTIME_TEST 宏跳过 */
#ifndef SKIP_RUNTIME_TEST
    FILE *fp = popen("klystrack --version 2>&1", "r");
    if (!fp) {
        fprintf(stderr, "FAIL: cannot run klystrack --version\n");
        return 1;
    }
    char buf[256] = {0};
    size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
    int pc_ret = pclose(fp);
    if (pc_ret != 0) {
        int real_code = WIFEXITED(pc_ret) ? WEXITSTATUS(pc_ret) : -1;
        fprintf(stderr, "FAIL: klystrack --version exited with code %d (pclose raw %d)\n", real_code, pc_ret);
        return 1;
    }
    if (n == 0 || strlen(buf) == 0) {
        fprintf(stderr, "FAIL: klystrack --version produced no output\n");
        return 1;
    }
    printf("klystrack version: %s", buf);

    /* 3. klystrack --help 退出码 0 */
    int ret = system("klystrack --help > /dev/null 2>&1");
    if (ret != 0) {
        int real_code = WIFEXITED(ret) ? WEXITSTATUS(ret) : -1;
        fprintf(stderr, "FAIL: klystrack --help exited with code %d (system raw %d)\n", real_code, ret);
        return 1;
    }
    printf("klystrack --help OK\n");
#else
    printf("SKIP_RUNTIME_TEST: cross_building, klystrack binary not run on host\n");
#endif

    printf("klystrack smoke test PASSED\n");
    return 0;
}
