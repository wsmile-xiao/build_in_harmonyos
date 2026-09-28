/* test_ohos.c — iqueue 2.2 HarmonyOS PC 专项测试
 *
 * 独立于上游 src/test.c 与 test_package 消费者用例，验证 OHOS 平台交付面：
 *   O1  iqueue_t 多生产者/单消费者真实业务场景（2 个发送线程 + 1 个接收线程）
 *   O2  iqueue1_t 单生产者/单消费者场景
 *   O3  阻塞 send/recv + 关闭队列后的返回码路径
 * 仅使用已安装包公开头文件 iqueue.h 与 libiqueue.a。
 */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "iqueue.h"

#define NPROD 2
#define NMSGS 500

static int s_ok = 1;

static void chk(const char *name, int cond) {
    printf("%s: %s\n", name, cond ? "PASS" : "FAIL");
    if (!cond) s_ok = 0;
}

/* O1: 多生产者 → 单消费者 */
typedef struct {
    iqueue_t *q;
    int id;
} prod_arg_t;

static void *producer(void *arg) {
    prod_arg_t *pa = (prod_arg_t *)arg;
    for (int i = 0; i < NMSGS; ++i) {
        void *msg = malloc(sizeof(int));
        *(int *)msg = pa->id * NMSGS + i;
        if (send_iqueue(pa->q, msg) != 0) {
            free(msg);
            return (void *)1;
        }
    }
    return 0;
}

static void run_iqueue_t_test(void) {
    iqueue_t *q = NULL;
    if (new_iqueue(&q, 32u) != 0) { chk("O1 new_iqueue", 0); return; }

    pthread_t th[NPROD];
    prod_arg_t pa[NPROD];
    for (int i = 0; i < NPROD; ++i) {
        pa[i].q = q;
        pa[i].id = i;
        if (pthread_create(&th[i], 0, producer, &pa[i]) != 0) {
            chk("O1 pthread_create", 0);
        }
    }

    int received[NPROD] = {0};
    int total = NPROD * NMSGS;
    for (int n = 0; n < total; ++n) {
        void *msg = NULL;
        if (recv_iqueue(q, &msg) != 0) {
            chk("O1 recv_iqueue", 0);
            break;
        }
        int v = *(int *)msg;
        free(msg);
        if (v < 0 || v >= total) { chk("O1 payload range", 0); }
        else received[v / NMSGS]++;
    }
    for (int i = 0; i < NPROD; ++i) pthread_join(th[i], 0);
    chk("O1 multi-producer counts", received[0] == NMSGS && received[1] == NMSGS);

    close_iqueue(q);
    chk("O1 delete_iqueue", delete_iqueue(&q) == 0 && q == NULL);
}

/* O2: iqueue1_t 单生产者/单消费者 */
static void run_iqueue1_test(void) {
    iqueue1_t *q = NULL;
    if (new_iqueue1(&q, 16u) != 0) { chk("O2 new_iqueue1", 0); return; }

    static char payload[] = "ohos-iqueue1-payload";
    chk("O2 trysend_iqueue1", trysend_iqueue1(q, payload) == 0);
    void *out = NULL;
    chk("O2 tryrecv_iqueue1", tryrecv_iqueue1(q, &out) == 0 && out == payload);
    chk("O2 size_iqueue1", size_iqueue1(q) == 0);
    chk("O2 capacity_iqueue1", capacity_iqueue1(q) == 16);

    close_iqueue1(q);
    chk("O2 delete_iqueue1", delete_iqueue1(&q) == 0 && q == NULL);
}

/* O3: 关闭队列后 send/recv 的返回码路径 */
static void run_close_path_test(void) {
    iqueue_t *q = NULL;
    chk("O3 new_iqueue", new_iqueue(&q, 4u) == 0);
    close_iqueue(q);
    int rc = send_iqueue(q, (void *)0x1);
    chk("O3 send after close", rc != 0);
    chk("O3 delete_iqueue", delete_iqueue(&q) == 0);
}

int main(void) {
    run_iqueue_t_test();
    run_iqueue1_test();
    run_close_path_test();
    printf("iqueue OHOS test: %s\n", s_ok ? "ALL PASS" : "FAILED");
    return s_ok ? 0 : 1;
}
