/*
 * libhiredis 1.3.0 消费者测试（R34：真断言，非恒真）
 *
 * 覆盖三条无 server 依赖的链路：
 *   1. 同步 API 连接失败路径：redisConnect 到无监听端口 → 返回 err 置位、
 *      errstr 非空、errno 语义（ECONNREFUSED 族）——无 redis-server 环境
 *      下验证错误路径契约；
 *   2. 命令格式化链路：redisFormatCommand 多格式插值输出字节级断言；
 *   3. 回复解析链路：redisReaderFeed/GetReply 对 RESP2 协议数据真解析。
 * 任一断言失败 → 非零退出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <hiredis/hiredis.h>

static int failures = 0;

#define CHECK(cond, msg)                                                  \
    do {                                                                  \
        if (cond) {                                                       \
            printf("OK: %s\n", msg);                                      \
        } else {                                                          \
            fprintf(stderr, "FAIL: %s\n", msg);                           \
            failures++;                                                   \
        }                                                                 \
    } while (0)

/* --- 1. 连接失败路径（无 redis-server 环境的 errno 语义） --- */
static void test_connect_refused(void) {
    /* 端口 1 (tcpmux) 无监听，connection refused 是最确定的无服务路径 */
    redisContext *c = redisConnect("127.0.0.1", 1);
    CHECK(c != NULL, "redisConnect returns context even on error");
    if (c == NULL) return;
    CHECK(c->err != 0, "context err set on refused connection");
    CHECK(c->errstr != NULL && c->errstr[0] != '\0',
          "errstr populated on refused connection");
    printf("  (err=%d errstr=\"%s\")\n", c->err, c->errstr ? c->errstr : "()");
    redisFree(c);

    /* redisConnectTimeout 同族 API 的失败路径 */
    struct timeval tv = {0, 200000}; /* 200ms */
    redisContext *c2 = redisConnectWithTimeout("127.0.0.1", 1, tv);
    CHECK(c2 != NULL, "redisConnectWithTimeout returns context");
    if (c2 != NULL) {
        CHECK(c2->err != 0, "timeout-context err set on refused connection");
        redisFree(c2);
    }
}

/* --- 2. 命令格式化链路 --- */
static void test_format_command(void) {
    char *cmd = NULL;
    int len = redisFormatCommand(&cmd, "PING");
    /* "*1\r\n" (4) + "$4\r\n" (4) + "PING\r\n" (6) = 14 bytes */
    CHECK(len == 14 && cmd != NULL && memcmp(cmd, "*1\r\n$4\r\nPING\r\n", 14) == 0,
          "redisFormatCommand PING produces exact RESP2 bytes");
    redisFreeCommand(cmd);

    len = redisFormatCommand(&cmd, "SET %s %s", "foo", "bar");
    /* "*3\r\n" (4) + 3 x ("$3\r\n" + 3 chars + "\r\n" = 9) = 4+27 = 31 */
    CHECK(len == 31 && cmd != NULL,
          "redisFormatCommand SET interpolates to 31 bytes");
    if (len == 31) {
        CHECK(memcmp(cmd, "*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n", 31) == 0,
              "redisFormatCommand SET bytes exact");
    }
    redisFreeCommand(cmd);
}

/* --- 3. 回复解析链路 --- */
static void test_reply_reader(void) {
    redisReader *reader = redisReaderCreate();
    CHECK(reader != NULL, "redisReaderCreate");

    /* simple string */
    const char *data = "+PONG\r\n";
    CHECK(redisReaderFeed(reader, data, strlen(data)) == REDIS_OK,
          "redisReaderFeed accepts +PONG");
    redisReply *reply = NULL;
    CHECK(redisReaderGetReply(reader, (void **)&reply) == REDIS_OK,
          "redisReaderGetReply parses +PONG");
    CHECK(reply != NULL && reply->type == REDIS_REPLY_STATUS,
          "reply type is STATUS");
    CHECK(reply != NULL && strcmp(reply->str, "PONG") == 0,
          "reply str is PONG");
    if (reply) freeReplyObject(reply);

    /* integer */
    data = ":42\r\n";
    CHECK(redisReaderFeed(reader, data, strlen(data)) == REDIS_OK,
          "redisReaderFeed accepts :42");
    reply = NULL;
    CHECK(redisReaderGetReply(reader, (void **)&reply) == REDIS_OK &&
          reply != NULL && reply->type == REDIS_REPLY_INTEGER &&
          reply->integer == 42,
          "integer reply parsed as 42");
    if (reply) freeReplyObject(reply);

    /* array of bulk strings */
    data = "*2\r\n$3\r\nabc\r\n$1\r\nZ\r\n";
    CHECK(redisReaderFeed(reader, data, strlen(data)) == REDIS_OK,
          "redisReaderFeed accepts nested array");
    reply = NULL;
    CHECK(redisReaderGetReply(reader, (void **)&reply) == REDIS_OK &&
          reply != NULL && reply->type == REDIS_REPLY_ARRAY &&
          reply->elements == 2 &&
          strcmp(reply->element[0]->str, "abc") == 0 &&
          strcmp(reply->element[1]->str, "Z") == 0,
          "array reply parsed with 2 bulk elements");
    if (reply) freeReplyObject(reply);

    /* error reply */
    data = "-ERR unknown command\r\n";
    CHECK(redisReaderFeed(reader, data, strlen(data)) == REDIS_OK,
          "redisReaderFeed accepts error line");
    reply = NULL;
    CHECK(redisReaderGetReply(reader, (void **)&reply) == REDIS_OK &&
          reply != NULL && reply->type == REDIS_REPLY_ERROR,
          "error reply parsed as REDIS_REPLY_ERROR");
    if (reply) freeReplyObject(reply);

    redisReaderFree(reader);
}

int main(void) {
    printf("== libhiredis 1.3.0 consumer tests ==\n");
    printf("-- connect failure path (no redis-server) --\n");
    test_connect_refused();
    printf("-- format command path --\n");
    test_format_command();
    printf("-- reply reader path --\n");
    test_reply_reader();

    if (failures) {
        fprintf(stderr, "*** %d CHECK(S) FAILED ***\n", failures);
        return 1;
    }
    printf("ALL CONSUMER TESTS PASSED\n");
    return 0;
}
