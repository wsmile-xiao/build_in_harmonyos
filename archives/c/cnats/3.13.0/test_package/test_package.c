#include <nats.h>
#include <stdio.h>
#include <string.h>

/* 消费者验证：真实调用 cnats 库 API 并断言行为。
 * 1) 初始化库并读取版本；
 * 2) 创建/配置 options（含 TLS 选项，证明 TLS 已编入）；
 * 3) 连接不存在的服务器，断言返回 NATS_NO_SERVER（真实连接路径执行）。 */
int main(void)
{
    natsStatus s;
    natsOptions *opts = NULL;
    natsConnection *nc = NULL;

    if (nats_Open(-1) != NATS_OK)
    {
        fprintf(stderr, "nats_Open failed\n");
        return 1;
    }

    const char *ver = nats_GetVersion();
    if (ver == NULL || ver[0] == '\0')
    {
        fprintf(stderr, "empty library version\n");
        return 1;
    }

    s = natsOptions_Create(&opts);
    if (s != NATS_OK)
    {
        fprintf(stderr, "natsOptions_Create failed: %s\n", natsStatus_GetText(s));
        return 1;
    }
    if (natsOptions_SetURL(opts, "nats://127.0.0.1:1") != NATS_OK)
        return 1;
    if (natsOptions_SetAllowReconnect(opts, false) != NATS_OK)
        return 1;
    if (natsOptions_SetMaxReconnect(opts, 0) != NATS_OK)
        return 1;
    if (natsOptions_SetSecure(opts, 1) != NATS_OK)
    {
        fprintf(stderr, "TLS support missing: SetSecure failed\n");
        return 1;
    }

    s = natsConnection_Connect(&nc, opts);
    if (s != NATS_NO_SERVER)
    {
        fprintf(stderr, "expected NATS_NO_SERVER, got %d (%s)\n",
                (int) s, natsStatus_GetText(s));
        return 1;
    }

    natsOptions_Destroy(opts);
    nats_CloseAndWait(100);
    printf("cnats consumer test passed (library %s; connect-to-absent-server -> NATS_NO_SERVER)\n",
           ver);
    return 0;
}
