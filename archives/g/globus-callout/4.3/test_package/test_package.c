// test_package/test_package.c — globus-callout 4.3 consumer test (L1)
// 真实调用 globus_callout API：activate → handle_init → register → destroy
// → deactivate，验证库链接与 API 可调用；任一步失败 return 1。
#include <globus_module.h>
#include <globus_callout.h>
#include <stdio.h>

int main(void) {
    globus_result_t rc;
    globus_callout_handle_t handle = NULL;

    /* 1. 激活模块 */
    rc = globus_module_activate(GLOBUS_CALLOUT_MODULE);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-callout 4.3: FAIL (activate rc=%lu)\n",
                (unsigned long)rc);
        return 1;
    }

    /* 2. 初始化 handle */
    rc = globus_callout_handle_init(&handle);
    if (rc != GLOBUS_SUCCESS || handle == NULL) {
        fprintf(stderr, "test globus-callout 4.3: FAIL (handle_init rc=%lu)\n",
                (unsigned long)rc);
        globus_module_deactivate(GLOBUS_CALLOUT_MODULE);
        return 1;
    }

    /* 3. 注册一个不存在的 callout——预期失败但验证 register API 可调用 */
    rc = globus_callout_register(handle, "test_type",
                                 "nonexistent_lib.so", "nonexistent_sym");
    /* register 可能失败（库/符号不存在），但 API 本身应可调用不崩溃 */
    if (rc == GLOBUS_SUCCESS) {
        /* 不应成功——库不存在 */
        fprintf(stderr, "test globus-callout 4.3: WARN (register unexpectedly succeeded)\n");
    }

    /* 4. 销毁 handle */
    rc = globus_callout_handle_destroy(handle);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-callout 4.3: FAIL (handle_destroy rc=%lu)\n",
                (unsigned long)rc);
        globus_module_deactivate(GLOBUS_CALLOUT_MODULE);
        return 1;
    }

    /* 5. 反激活模块 */
    rc = globus_module_deactivate(GLOBUS_CALLOUT_MODULE);
    if (rc != GLOBUS_SUCCESS) {
        fprintf(stderr, "test globus-callout 4.3: FAIL (deactivate rc=%lu)\n",
                (unsigned long)rc);
        return 1;
    }

    printf("test globus-callout 4.3: OK "
           "(activate→handle_init→register→destroy→deactivate all callable)\n");
    return 0;
}
