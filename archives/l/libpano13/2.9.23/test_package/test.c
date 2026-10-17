#include <stdio.h>
#include <string.h>
#include "panorama.h"
#include "filter.h"

/* 实质调用 libpano13 公开 API 的消费者测试：
 *  1. panoProjectionFormatCount() —— 查询库注册的投影格式数量（panorama.h），断言 > 0
 *  2. PT_setProgressFcn()/PT_setInfoDlgFcn() —— 设置回调并触发 Progress()（filter.h）
 *  3. queryFOVLimits() —— 查询投影视场角限制（panorama.h），断言返回成功且视场角合理
 */
static int progress_cb(int command, char *argument)
{
    (void)command;
    (void)argument;
    return 0;
}

int main(void)
{
    int failures = 0;

    int count = panoProjectionFormatCount();
    if (count <= 0) {
        fprintf(stderr, "FAIL: panoProjectionFormatCount() = %d (expected > 0)\n", count);
        failures++;
    } else {
        printf("panoProjectionFormatCount() = %d\n", count);
    }

    PT_setProgressFcn(progress_cb);
    PT_setInfoDlgFcn(progress_cb);
    /* Progress(0, NULL) 触发注册的进度回调（0=Init 命令），不崩溃即回调链路正常 */
    Progress(0, (char *)"test");

    /* projection=1（_rectilinear），params 为 0 表示默认参数；
       lims[0]=maxhfov, lims[1]=maxvfov；上游源码返回 0=失败、1=成功 */
    double params[8] = {0};
    double lims[2] = {0};
    int fov = queryFOVLimits(1, params, lims);
    if (fov != 1) {
        fprintf(stderr, "FAIL: queryFOVLimits(1) rc=%d (expected 1)\n", fov);
        failures++;
    } else {
        printf("queryFOVLimits(1) -> rc=%d maxhfov=%.1f maxvfov=%.1f\n", fov, lims[0], lims[1]);
    }
    if (lims[0] <= 0 || lims[1] <= 0) {
        fprintf(stderr, "FAIL: queryFOVLimits lims maxhfov=%.1f maxvfov=%.1f (expected > 0)\n",
                lims[0], lims[1]);
        failures++;
    }

    if (failures > 0) {
        fprintf(stderr, "libpano13 test FAILED: %d assertion(s)\n", failures);
        return 1;
    }
    printf("libpano13 test OK (3 API assertions)\n");
    return 0;
}
