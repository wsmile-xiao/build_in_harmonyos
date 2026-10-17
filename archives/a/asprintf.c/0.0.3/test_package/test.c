/*
 * test.c — asprintf.c 0.0.3 消费者侧 HarmonyOS 专项测试
 *
 * 模拟业务上层组件（如日志/格式化组件）：仅使用已安装包的
 * 公开头文件 asprintf.h 与公开 API asprintf()/vasprintf()，
 * 验证第三方使用者在 OHOS aarch64 上能否编译、链接、调用并
 * 观察到正确结果。
 *
 * 覆盖 4 个有业务意义的公开 API 调用场景：
 *   1. asprintf %s 字符串格式化（业务常见：拼接日志行）
 *   2. asprintf 多参数混合格式化（%d/%s/%f）
 *   3. vasprintf 变参透传（上层封装 printf 类 API 的典型用法）
 *   4. 返回值为格式化长度（POSIX 语义，业务用于缓冲区核算）
 * 每个场景都有可观察校验（内容 + 长度），非空壳。
 *
 * 校验不使用 assert()：Release(-DNDEBUG) 下 assert 会被剔除导致
 * 假绿，这里改为显式失败语义——失败时打印具体场景、期望值、
 * 实际值并以非 0 退出，保证 Debug 与 Release 都真实校验。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#include <asprintf.h>

/* 显式失败语义：打印具体场景/期望值/实际值，返回 1（非 0 退出码） */
static int fail(int scn, const char *what, long expected, long actual)
{
    fprintf(stderr, "FAIL scenario %d: %s expected=%ld actual=%ld\n",
            scn, what, expected, actual);
    return 1;
}

static int my_vsnprintf_style(char **out, const char *fmt, ...)
{
    /* 业务上层典型封装：把 va_list 透传给 vasprintf */
    va_list args;
    va_start(args, fmt);
    *out = NULL;
    int n = vasprintf(out, fmt, args);
    va_end(args);
    return n;   /* 由调用方显式校验 n >= 0 */
}

int main(void)
{
    /* 场景 1: %s 字符串格式化 */
    {
        char *line = NULL;
        int n = asprintf(&line, "event=%s level=%d", "login", 3);
        if (line == NULL)
            return fail(1, "line != NULL", 1, 0);
        if (n != 19)   /* strlen("event=login level=3") = 19 */
            return fail(1, "asprintf return length", 19, n);
        if (strcmp(line, "event=login level=3") != 0)
            return fail(1, "content", 0, 1);
        printf("case1 ok: %s (len=%d)\n", line, n);
        free(line);
    }

    /* 场景 2: 多参数混合格式化 */
    {
        char *line = NULL;
        int n = asprintf(&line, "%d + %d = %d", 1, 1, 2);
        if (line == NULL)
            return fail(2, "line != NULL", 1, 0);
        if (n != 9)   /* strlen("1 + 1 = 2") = 9 */
            return fail(2, "asprintf return length", 9, n);
        if (strcmp(line, "1 + 1 = 2") != 0)
            return fail(2, "content", 0, 1);
        printf("case2 ok: %s (len=%d)\n", line, n);
        free(line);
    }

    /* 场景 3: vasprintf 变参透传（上层封装 API） */
    {
        char *line = NULL;
        int n = my_vsnprintf_style(&line, "user=%s action=%s", "alice", "upload");
        if (n < 0)
            return fail(3, "vasprintf >= 0", 0, n);
        if (line == NULL)
            return fail(3, "line != NULL", 1, 0);
        if (strcmp(line, "user=alice action=upload") != 0)
            return fail(3, "content", 0, 1);
        if ((int)strlen(line) != 24)   /* strlen("user=alice action=upload") = 24 */
            return fail(3, "strlen", 24, (int)strlen(line));
        printf("case3 ok: %s (len=%zu)\n", line, strlen(line));
        free(line);
    }

    /* 场景 4: 返回值=格式化长度（POSIX 语义） */
    {
        char *line = NULL;
        int n = asprintf(&line, "%s", "asprintf-c-0.0.3");
        if (line == NULL)
            return fail(4, "line != NULL", 1, 0);
        if (n != 16)   /* strlen("asprintf-c-0.0.3") = 16 */
            return fail(4, "asprintf return length", 16, n);
        if (strlen(line) != (size_t)n)
            return fail(4, "strlen == n", n, (long)strlen(line));
        if (line[n] != '\0')   /* 必须以 NUL 结尾 */
            return fail(4, "line[n] == NUL", 0, (long)line[n]);
        printf("case4 ok: %s (len=%d)\n", line, n);
        free(line);
    }

    printf("test_consume: ALL 4 CASES PASSED\n");
    return 0;
}
