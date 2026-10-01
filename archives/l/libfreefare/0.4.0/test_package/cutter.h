/* cutter.h — Cutter 框架兼容 shim（不引入 Cutter 运行时）
 *
 * 把上游 Cutter 断言宏映射到标准 assert，使上游纯计算测试用例
 * 能在无 Cutter 框架的环境下直接编译执行。
 */
#ifndef __CUTTER_SHIM_H__
#define __CUTTER_SHIM_H__

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#define cut_message(msg) (msg)

static inline int __cut_assert_equal_int(int expected, int actual, const char *msg) {
    if (expected != actual) {
        fprintf(stderr, "  [FAIL] %s: expected %d, got %d\n", msg, expected, actual);
        return 1;
    }
    return 0;
}

#define cut_assert_equal_int(expected, actual, msg) do { \
    if (__cut_assert_equal_int((expected), (actual), (msg))) exit(1); \
} while (0)

#define cut_assert_not_null(ptr, msg) do { \
    if ((ptr) == NULL) { \
        fprintf(stderr, "  [FAIL] %s: expected non-NULL\n", msg); \
        exit(1); \
    } \
} while (0)

#define cut_assert_null(ptr, msg) do { \
    if ((ptr) != NULL) { \
        fprintf(stderr, "  [FAIL] %s: expected NULL\n", msg); \
        exit(1); \
    } \
} while (0)

static inline int __cut_assert_equal_memory(const void *expected, size_t expected_len,
                                             const void *actual, size_t actual_len,
                                             const char *msg) {
    if (expected_len != actual_len) {
        fprintf(stderr, "  [FAIL] %s: length mismatch, expected %zu, got %zu\n",
                msg, expected_len, actual_len);
        return 1;
    }
    if (memcmp(expected, actual, expected_len) != 0) {
        fprintf(stderr, "  [FAIL] %s: memory mismatch\n", msg);
        return 1;
    }
    return 0;
}

#define cut_assert_equal_memory(expected, expected_len, actual, actual_len, msg) do { \
    if (__cut_assert_equal_memory((expected), (expected_len), (actual), (actual_len), (msg))) exit(1); \
} while (0)

#endif /* __CUTTER_SHIM_H__ */
