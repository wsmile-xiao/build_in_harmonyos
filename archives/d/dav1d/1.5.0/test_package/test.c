/* dav1d 1.5.0 —— 真实解码器生命周期验证（非 dlopen 空壳）。
 *
 * 判据设计（都可离线核验，不需要 AV1 码流样本）：
 *   ① dav1d_version() 必须与本包版本一致 —— 证明装上的是这一版，不是设备上别的残留；
 *   ② dav1d_default_settings() 填出的默认值要落在合法区间（n_threads >= 0 等）；
 *   ③ dav1d_open() 真能开出解码器上下文、dav1d_close() 能正常收回 ——
 *      这一步会真正走内部内存分配与线程池初始化，是「库能用」的最小实证；
 *   ④ 传非法参数（n_threads 超上限）时 dav1d_open 必须**报错而非成功** ——
 *      只验成功路径的话，一个永远 return 0 的桩实现也能蒙混过关。
 *
 * 头路径查过上游 include/ 实际布局：是 <dav1d/dav1d.h>，不是 <dav1d.h>。
 */
#include <dav1d/dav1d.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);\
            ++failures;                                                        \
        } else {                                                               \
            printf("[ok] %s\n", (msg));                                        \
        }                                                                      \
    } while (0)

int main(void) {
    const char *ver = dav1d_version();
    printf("     dav1d 版本: %s\n", ver ? ver : "(null)");
    CHECK(ver != NULL && strncmp(ver, "1.5.0", 5) == 0, "dav1d_version() == 1.5.0");

    Dav1dSettings s;
    memset(&s, 0, sizeof(s));
    dav1d_default_settings(&s);
    CHECK(s.n_threads >= 0, "默认 n_threads 合法（>= 0）");
    CHECK(s.max_frame_delay >= 0, "默认 max_frame_delay 合法（>= 0）");

    /* ③ 真开一个解码器上下文——会走内部分配与线程池初始化 */
    Dav1dContext *c = NULL;
    int rc = dav1d_open(&c, &s);
    CHECK(rc == 0 && c != NULL, "dav1d_open() 成功开出上下文");
    if (rc == 0 && c != NULL) {
        dav1d_flush(c);                     /* 空 flush 应安全 */
        printf("[ok] dav1d_flush() 未崩溃\n");
        dav1d_close(&c);
        CHECK(c == NULL, "dav1d_close() 后上下文被置空");
    }

    /* ④ 非法参数必须被拒 —— 区分「真实现」与「永远成功的桩」 */
    Dav1dSettings bad;
    dav1d_default_settings(&bad);
    bad.n_threads = 1 << 20;                /* 远超上限 */
    Dav1dContext *c2 = NULL;
    int rc2 = dav1d_open(&c2, &bad);
    CHECK(rc2 != 0, "非法 n_threads 被 dav1d_open() 拒绝（证明参数校验真在跑）");
    if (rc2 == 0 && c2) dav1d_close(&c2);

    if (failures) {
        fprintf(stderr, "\ndav1d: %d 项断言失败\n", failures);
        return 1;
    }
    printf("\ndav1d 1.5.0: 全部断言通过\n");
    return 0;
}
