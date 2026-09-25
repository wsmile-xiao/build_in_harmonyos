#include <stdio.h>
#include <stdlib.h>
#include <debuginfod.h>

/* 消费者测试:真实链接并调用 libdebuginfod 客户端 API。
 * DEBUGINFOD_URLS 指向本机未监听端口:连接立即被拒,API 按文档返回
 * 负的 POSIX 错误码(不崩溃、不挂网)。句柄创建/查询/销毁全链路真实执行。 */
int main(void)
{
    setenv("DEBUGINFOD_URLS", "http://127.0.0.1:1", 1);
    setenv("DEBUGINFOD_TIMEOUT", "2", 1);
    setenv("DEBUGINFOD_RETRY_LIMIT", "0", 1);

    debuginfod_client *client = debuginfod_begin();
    if (client == NULL) {
        fprintf(stderr, "debuginfod_begin failed\n");
        return 1;
    }
    unsigned char build_id[8] = {0xde, 0xad, 0xbe, 0xef, 0, 0, 0, 1};
    char *path = NULL;
    int rc = debuginfod_find_debuginfo(client, build_id, sizeof(build_id), &path);
    printf("debuginfod_find_debuginfo rc=%d (expect negative: server unreachable)\n", rc);
    free(path);
    debuginfod_end(client);
    /* 不可达服务必须返回负错误码;返回 0(拿到 fd)才是异常 */
    return rc < 0 ? 0 : 1;
}
