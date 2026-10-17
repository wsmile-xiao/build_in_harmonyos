/* remctl 3.18 test_package —— 真实调用 libremctl 公共 API 并以断言决定退出码。
 * 依据 client/remctl.h：remctl_new/remctl_open/remctl_error/remctl_close/remctl_result_free。
 * 断言全部走"无服务端环境下的确定失败路径"，不需要 KDC/remctld，因此在本平台可真跑（§10.1 赛道二）。 */
#include <stdio.h>
#include <string.h>
#include <remctl.h>

static int tested = 0;
static int fails = 0;
#define CHECK(cond, msg) do { if (!(cond)) { printf("not ok %d - %s\n", ++tested, msg); fails++; } \
                              else { printf("ok %d - %s\n", ++tested, msg); } } while (0)

int main(void) {
    struct remctl *r;
    struct remctl_result *res;

    /* A1: 句柄分配并初始化 */
    r = remctl_new();
    CHECK(r != NULL, "remctl_new returns a handle");

    /* A2: 连到本机确定关闭的端口必须失败（返回 0），且错误串非空 */
    if (r) {
        int opened = remctl_open(r, "127.0.0.1", 1, NULL);
        CHECK(opened == 0, "remctl_open to closed port fails");
        const char *err = remctl_error(r);
        CHECK(err != NULL && strlen(err) > 0, "remctl_error yields a non-empty message");
        remctl_close(r);
    }

    /* A3: 一次性 API 同样走失败路径，返回结果且可安全释放。
     * 真实签名（client/remctl.h:152）是 4 参、command 为 NULL 结尾的 argv 向量：
     *   struct remctl_result *remctl(const char *host, unsigned short port,
     *                                const char *principal, const char **command)
     * 早先按 5 参 (…, "test", NULL) 写会直接编译失败：too many arguments to function call。 */
    {
        const char *cmd[] = { "test", NULL };
        res = remctl("127.0.0.1", 1, NULL, cmd);
    }
    CHECK(res != NULL, "one-shot remctl returns a result struct");
    if (res) {
        CHECK(res->status != 0 || res->error != NULL, "one-shot result reports failure");
        remctl_result_free(res);
    }

    printf("1..%d\n", tested);
    return fails == 0 ? 0 : 1;
}
