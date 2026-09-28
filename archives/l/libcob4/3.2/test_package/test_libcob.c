/*
 * test_libcob.c — consumer-side test for the packaged libcob4 (libcob.so.4).
 *
 * 这个程序只使用 GnuCOBOL **公开**的 libcob C API（<libcob.h>），不碰任何内部头：
 *
 *   api    模式：运行时全生命周期 —— 初始化状态机 / 内存 API / 字段到字符串的
 *                边界截断 / 运行时自己的 getpid 绑定。全部通过退出码 0 表达。
 *   tmpdir 模式：调用公开 API cob_temp_name()，把运行时解析出的临时文件**全路径**
 *                打到 stdout（TEMPNAME=<path>）。临时目录的解析结果在 libcob 内
 *                是**进程内静态缓存**（common.c 的 cob_gettmpdir() 静态 tmpdir），
 *                所以每换一个 TMPDIR 都必须换一个新进程 —— 由 test_libcob.sh 驱动。
 */
#include <libcob.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define FAIL(msg)                                                       \
    do {                                                                \
        fprintf(stderr, "libcob4 test FAIL: %s\n", (msg));              \
        return 1;                                                       \
    } while (0)

/* ---- api 模式 ---------------------------------------------------------- */

static int check_memory_api(void)
{
    const char expected[] = "libcob API: OK";
    char *buffer = cob_malloc(sizeof(expected));

    if (!buffer) {
        FAIL("cob_malloc returned NULL");
    }
    memcpy(buffer, expected, sizeof(expected));
    if (strcmp(buffer, expected) != 0) {
        cob_free(buffer);
        FAIL("cob_malloc/cob_free round-trip lost the payload");
    }
    cob_free(buffer);
    return 0;
}

static int check_field_string_bounds(void)
{
    static const cob_field_attr attr = {
        COB_TYPE_ALPHANUMERIC, 0, 0, 0, NULL
    };
    unsigned char source[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    cob_field field = {sizeof(source) - 1, source, &attr};
    struct {
        char buffer[8];
        unsigned char sentinel[64];
    } output;
    size_t i;

    memset(&output, 0xA5, sizeof(output));
    cob_get_field_str(&field, output.buffer, sizeof(output.buffer));

    /* 26 字节字段塞进 8 字节缓冲：必须截断 + 终止，且绝不越界写 */
    for (i = 0; i < sizeof(output.sentinel); ++i) {
        if (output.sentinel[i] != 0xA5) {
            FAIL("cob_get_field_str wrote past the caller's buffer");
        }
    }
    if (memcmp(output.buffer, "ABCDEFG", 7) != 0 || output.buffer[7] != '\0') {
        FAIL("cob_get_field_str did not truncate to 7 chars + NUL");
    }
    return 0;
}

static int check_sys_getpid(void)
{
    int runtime_pid;
    int libc_pid;

    runtime_pid = cob_sys_getpid();
    libc_pid = (int) getpid();
    if (runtime_pid <= 0) {
        FAIL("cob_sys_getpid() returned a non-positive pid");
    }
    if (runtime_pid != libc_pid) {
        FAIL("cob_sys_getpid() disagrees with libc getpid()");
    }
    return 0;
}

static int run_api_mode(int argc, char **argv)
{
    cob_module *module = NULL;
    cob_global *global = NULL;
    int result;

    if (cob_is_initialized()) {
        FAIL("cob_is_initialized() was true before cob_init()");
    }

    cob_init(argc, argv);

    if (!cob_is_initialized()) {
        FAIL("cob_is_initialized() is still false after cob_init()");
    }

    cob_module_enter(&module, &global, 0);

    result = check_memory_api()
          || check_field_string_bounds()
          || check_sys_getpid();

    cob_module_leave(module);
    cob_tidy();
    return result;
}

/* ---- tmpdir 模式 ------------------------------------------------------- */

static int run_tmpdir_mode(int argc, char **argv)
{
    char name[4096];
    const char *tmpdir_env;

    cob_init(argc, argv);

    name[0] = 0;
    cob_temp_name(name, "t");
    if (name[0] == 0) {
        FAIL("cob_temp_name() produced an empty path");
    }

    printf("TEMPNAME=%s\n", name);

    /* libcob 会把解析结果写回环境，供它 fork 出去的外部工具使用 */
    tmpdir_env = getenv("TMPDIR");
    printf("TMPDIR_ENV=%s\n", tmpdir_env ? tmpdir_env : "(unset)");

    printf("NEEDS_FRESH_PROCESS=%s\n", "yes");
    return 0;
}

/* ---- 入口 -------------------------------------------------------------- */

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s api|tmpdir\n", argv[0]);
        return 2;
    }
    if (strcmp(argv[1], "api") == 0) {
        return run_api_mode(argc, argv);
    }
    if (strcmp(argv[1], "tmpdir") == 0) {
        return run_tmpdir_mode(argc, argv);
    }
    fprintf(stderr, "unknown mode: %s\n", argv[1]);
    return 2;
}
