/* test_package 消费者测试：真实调用 civetweb C API
 * 验证 libcivetweb 可链接、可初始化、可启动/停止 HTTP 服务上下文。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "civetweb.h"

static int hello_handler(struct mg_connection *conn, void *cbdata)
{
    const char *body = "hello civetweb";
    (void)cbdata;
    mg_printf(conn,
              "HTTP/1.1 200 OK\r\n"
              "Content-Type: text/plain\r\n"
              "Content-Length: %d\r\n"
              "Connection: close\r\n"
              "\r\n"
              "%s",
              (int)strlen(body), body);
    return 200;
}

int main(void)
{
    const char *options[] = {"listening_ports", "127.0.0.1:0", NULL};
    struct mg_init_data init;
    struct mg_error_data error;
    struct mg_context *ctx;
    unsigned feat = mg_init_library(MG_FEATURES_FILES);
    if ((feat & MG_FEATURES_FILES) == 0) {
        /* MG_FEATURES_DEFAULT=0，请求 0 特性时返回 0 是正常；
         * 请求 FILES 特性必须按位命中
         */
        fprintf(stderr, "mg_init_library failed (features=0x%x)\n", feat);
        return 1;
    }

    memset(&init, 0, sizeof(init));
    init.configuration_options = options;
    memset(&error, 0, sizeof(error));
    memset(&error, 0, sizeof(error.text));
    ctx = mg_start2(&init, &error);
    if (ctx == NULL) {
        fprintf(stderr, "mg_start2 failed: %s\n", error.text);
        mg_exit_library();
        return 1;
    }

    mg_set_request_handler(ctx, "/hello", hello_handler, NULL);
    mg_stop(ctx);
    mg_exit_library();

    printf("civetweb consumer test: OK\n");
    return 0;
}