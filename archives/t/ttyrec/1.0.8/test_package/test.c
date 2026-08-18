/* test.c — 参考程序，用于 ttyrec 录制/回放测试的基础程序 */
#include <time.h>

int main(void) {
    time_t t = time(NULL);
    return t == (time_t)-1 ? 1 : 0;
}
