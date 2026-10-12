/* OHOS 消费者探针 —— 把 thunk_gen（thunk_type=0）生成的 C 派发表当作
 * 真实消费者产物使用。
 *
 * 下游工程（dj64dev 的 src/thunks_c.c 等）拿到 thunk_gen 生成的
 * thunk_calls.h 后，是把它 include 进一个 switch 里，并自己提供
 * _DISPATCH / _DISPATCH_v 以及参数编组宏 _ARG / _ARG_PTR / _ARG_R / _RET。
 * 本探针复刻这一用法：**真实编译、链接、运行**，然后逐条核对
 * “case 编号 -> 被调函数 / 返回宽度 / 参数编组描述”是否与
 * src/thunk_gen.y 的文法语义一致。
 *
 * 期望值（由文法推导，非拷贝工具输出）：
 *   case 0  _dos_open  void( const char *path@0, int flags@4 )
 *   case 1  _dos_close unsigned int( int fd@0 )   返回宽度 4
 *   case 2  _dos_putc  void( unsigned char c@0 )
 *   case 3  _dos_exit  void NORETURN( int code@0 )
 *
 * 输出：逐条打印实际观测到的派发记录，最后一行
 *   OHOS_CONSUMER_C checks=<n> passed=<n> failed=<n>
 * 退出码 0 表示全部断言通过。
 */
#include <stdio.h>
#include <string.h>

/* ── 消费者侧的参数编组宏（真实消费者在此处做 32 位栈/寄存器搬运）── */
#define _SP 0
#define _RET 0
#define _ARG_R(t) 0
#define _ARG(off, t, sp) (off)
#define _ARG_PTR(off, t, sp) (off)

#define MAX_RECORDS 16

struct dispatch_record {
    const char *name;
    int is_void;      /* 1 = _DISPATCH_v 形式 */
    int retlen;       /* 非 void 形式的返回字节数，void 记 -1 */
    const char *args; /* 参数编组描述原文 */
};

static struct dispatch_record g_records[MAX_RECORDS];
static int g_count = 0;
static int g_overflow = 0;

static void record(const char *name, int is_void, int retlen, const char *args)
{
    if (g_count < MAX_RECORDS) {
        g_records[g_count].name = name;
        g_records[g_count].is_void = is_void;
        g_records[g_count].retlen = retlen;
        g_records[g_count].args = args;
    } else {
        g_overflow = 1;
    }
    g_count++;
}

/* 生成物里 void 返回写作 _DISPATCH_v(name[, args...])；参数列表用字符串
 * 原样捕获，既能覆盖“无参”形态，又不依赖 __VA_OPT__ 等扩展。 */
#define _DISPATCH_v(name, ...) record(#name, 1, -1, #__VA_ARGS__)
#define _DISPATCH(retlen, argr, ret, name, ...) \
    record(#name, 0, (retlen), #__VA_ARGS__)

/* 消费者的派发入口：include 生成物，构造成 switch 主体 */
static void dispatch(int id)
{
    switch (id) {
#include "thunk_calls.h"
    default:
        record("<no-such-thunk>", 0, -1, "");
        break;
    }
}

/* ── 断言框架 ── */
static int g_checks = 0;
static int g_fails = 0;

static void check_str(const char *what, const char *expected, const char *actual)
{
    g_checks++;
    if (actual != NULL && strcmp(expected, actual) == 0) {
        printf("  [ok]   %s\n", what);
    } else {
        g_fails++;
        printf("  [FAIL] %s [expected=%s actual=%s]\n", what, expected,
               actual == NULL ? "<null>" : actual);
    }
}

static void check_int(const char *what, int expected, int actual)
{
    g_checks++;
    if (expected == actual) {
        printf("  [ok]   %s\n", what);
    } else {
        g_fails++;
        printf("  [FAIL] %s [expected=%d actual=%d]\n", what, expected, actual);
    }
}

int main(void)
{
    static const struct {
        const char *name;
        int is_void;
        int retlen;
        const char *args;
    } expected[] = {
        { "_dos_open",  1, -1, "_ARG_PTR(0, const char, _SP), _ARG(4, DWORD, _SP)" },
        { "_dos_close", 0,  4, "_ARG(0, DWORD, _SP)" },
        { "_dos_putc",  1, -1, "_ARG(0, UBYTE, _SP)" },
        { "_dos_exit",  1, -1, "_ARG(0, DWORD, _SP)" },
    };
    const int n_expected = (int)(sizeof(expected) / sizeof(expected[0]));
    int i;

    /* 按消费者习惯：逐 thunk 编号调用派发入口 */
    for (i = 0; i < n_expected; i++) {
        dispatch(i);
    }

    printf("OHOS consumer C dispatch probe (aarch64 OHOS)\n");
    for (i = 0; i < g_count && i < MAX_RECORDS; i++) {
        printf("  #%d %s kind=%s retlen=%d args=%s\n", i, g_records[i].name,
               g_records[i].is_void ? "void" : "value", g_records[i].retlen,
               g_records[i].args);
    }

    check_int("派发条目数与声明数一致", n_expected, g_count);
    check_int("未发生记录溢出", 0, g_overflow);

    for (i = 0; i < n_expected && i < g_count && i < MAX_RECORDS; i++) {
        char what[128];
        snprintf(what, sizeof(what), "case %d 符号名", i);
        check_str(what, expected[i].name, g_records[i].name);
        snprintf(what, sizeof(what), "case %d 返回形态", i);
        check_int(what, expected[i].is_void, g_records[i].is_void);
        snprintf(what, sizeof(what), "case %d 返回宽度", i);
        check_int(what, expected[i].retlen, g_records[i].retlen);
        snprintf(what, sizeof(what), "case %d 参数编组", i);
        check_str(what, expected[i].args, g_records[i].args);
    }

    /* switch 只应包含 4 个 case：越界编号必须落到 default */
    dispatch(n_expected + 41);
    check_int("越界编号落在 default 分支", n_expected + 1, g_count);
    check_str("default 分支未误派发", "<no-such-thunk>",
              g_records[g_count - 1].name);

    printf("OHOS_CONSUMER_C checks=%d passed=%d failed=%d\n", g_checks,
           g_checks - g_fails, g_fails);
    return g_fails == 0 ? 0 : 1;
}
