#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <hiredis/hiredis.h>

int main(void) {
    int failures = 0;

    /* Test 1: redisFormatCommand - format a simple command */
    char *cmd = NULL;
    int len = redisFormatCommand(&cmd, "PING");
    if (len <= 0 || cmd == NULL) {
        fprintf(stderr, "FAIL: redisFormatCommand returned len=%d\n", len);
        failures++;
    } else {
        printf("OK: redisFormatCommand formatted \"%s\" (len=%d)\n", cmd, len);
        redisFreeCommand(cmd);
    }

    /* Test 2: redisFormatCommand with arguments */
    cmd = NULL;
    len = redisFormatCommand(&cmd, "SET %s %s", "key", "value");
    if (len <= 0 || cmd == NULL) {
        fprintf(stderr, "FAIL: redisFormatCommand (args) returned len=%d\n", len);
        failures++;
    } else {
        printf("OK: redisFormatCommand (args) formatted \"%s\" (len=%d)\n", cmd, len);
        redisFreeCommand(cmd);
    }

    /* Test 3: redisReaderCreate + freeReplyObject */
    redisReader *reader = redisReaderCreate();
    if (reader == NULL) {
        fprintf(stderr, "FAIL: redisReaderCreate returned NULL\n");
        failures++;
    } else {
        printf("OK: redisReaderCreate succeeded\n");

        /* Feed a simple reply and parse it */
        const char *reply_str = "+PONG\r\n";
        int ret = redisReaderFeed(reader, reply_str, strlen(reply_str));
        if (ret != REDIS_OK) {
            fprintf(stderr, "FAIL: redisReaderFeed returned %d\n", ret);
            failures++;
        } else {
            void *reply = NULL;
            ret = redisReaderGetReply(reader, &reply);
            if (ret != REDIS_OK || reply == NULL) {
                fprintf(stderr, "FAIL: redisReaderGetReply returned %d\n", ret);
                failures++;
            } else {
                redisReply *r = (redisReply *)reply;
                if (r->type != REDIS_REPLY_STATUS) {
                    fprintf(stderr, "FAIL: unexpected reply type %d\n", r->type);
                    failures++;
                } else {
                    printf("OK: parsed reply status = \"%s\"\n", r->str);
                }
                freeReplyObject(reply);
            }
        }
        redisReaderFree(reader);
    }

    /* Test 4: redisConnect with invalid address (should fail gracefully) */
    redisContext *c = redisConnect("127.0.0.1", 65535);
    if (c == NULL) {
        fprintf(stderr, "FAIL: redisConnect returned NULL (allocation failure)\n");
        failures++;
    } else {
        if (c->err != 0) {
            printf("OK: redisConnect returned error as expected: %s\n", c->errstr);
        } else {
            printf("OK: redisConnect succeeded (unexpected but not a failure)\n");
            redisFree(c);
            c = NULL;
        }
    }
    if (c) redisFree(c);

    if (failures > 0) {
        fprintf(stderr, "FAILED: %d test(s) failed\n", failures);
        return 1;
    }

    printf("All hiredis API tests passed.\n");
    return 0;
}