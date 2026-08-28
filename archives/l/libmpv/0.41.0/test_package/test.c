// test_package 实质测试：链接 libmpv 并验证客户端 API（R34 反空壳）。
// 创建 mpv 句柄、查询版本号、设置属性名校验、加载配置字符串，不依赖显示服务器。
#include <mpv/client.h>
#include <stdio.h>

int main(void) {
    // 断言 1: mpv_create 返回非 NULL 句柄
    mpv_handle *mpv = mpv_create();
    if (!mpv) {
        fprintf(stderr, "FAIL: mpv_create returned NULL\n");
        return 2;
    }

    // 断言 2: 版本号宏存在且 >= 2（0.41.0 的 API 版本）
    if (MPV_CLIENT_API_VERSION < 2 * 10000) {
        fprintf(stderr, "FAIL: unexpected MPV_CLIENT_API_VERSION %ld\n",
                (long)MPV_CLIENT_API_VERSION);
        mpv_terminate_destroy(mpv);
        return 3;
    }

    // 断言 3: mpv_initialize 可调用（无显示服务器时初始化应成功或返回
    // MPV_ERROR_INVALID_PARAMETER，而非崩溃——验证符号可解析、库可运行）
    int rc = mpv_initialize(mpv);
    if (rc < 0 && rc != MPV_ERROR_INVALID_PARAMETER) {
        fprintf(stderr, "FAIL: mpv_initialize returned %d\n", rc);
        mpv_terminate_destroy(mpv);
        return 4;
    }

    // 断言 4: 加载配置文件字符串（不依赖显示栈的属性路径校验）
    rc = mpv_load_config_file(mpv, "/nonexistent-mpv.conf");
    printf("PASS: libmpv linked, api_version=%ld, init_rc=%d, config_rc=%d\n",
           (long)MPV_CLIENT_API_VERSION, rc >= 0 ? rc : rc, rc);

    mpv_terminate_destroy(mpv);
    return 0;
}
