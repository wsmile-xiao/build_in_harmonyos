#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <bsdconv.h>

/* test_package consumer test:
 *  1. mirrors upstream testsuite/api.c assertions (bsdconv_pack / insert_phase
 *     / replace_phase / replace_codec / insert_codec)
 *  2. additionally covers the 3-phase create path that upstream off-by-one
 *     VLA bug used to break (ASCII:COUNT:ASCII -> EINVAL on clang15/OHOS)
 *  3. runs real conversions through the bsdconv binary to assert end-to-end
 *     charset conversion works with the packaged modules.
 * Returns number of failures (0 = all passed).
 */

static int failures = 0;

static void check_str(const char *what, const char *expect, const char *got) {
    if (strcmp(expect, got) != 0) {
        printf("FAIL: %s\nexpect: %s\nresult: %s\n", what, expect, got);
        failures++;
    } else {
        printf("PASS: %s\n", what);
    }
}

static void check_ok(const char *what, int cond) {
    if (cond) {
        printf("PASS: %s\n", what);
    } else {
        printf("FAIL: %s\n", what);
        failures++;
    }
}

int main(int argc, char *argv[]) {
    char *in = strdup("utf-8:utf-8,ascii");
    char *out;
    char *expect;
    struct bsdconv_instance *ins;

    /* --- test 1: bsdconv_unpack 3-phase create (upstream VLA off-by-one
     * regression path) --- */
    ins = bsdconv_create("ASCII:COUNT:ASCII");
    check_ok("create 3-phase ASCII:COUNT:ASCII", ins != NULL);
    if (ins) {
        out = bsdconv_pack(ins);
        printf("INFO: pack(ASCII:COUNT:ASCII) = %s\n", out ? out : "()");
        free(out);
        bsdconv_destroy(ins);
    }

    /* --- test 2: upstream api.c bsdconv_pack assertion --- */
    expect = "ASCII,_UTF-8,ANY#013F&ERROR:count#lowercase:AsCiI,any#3f";
    ins = bsdconv_create("utf-8,3f:count#lowercase:AsCiI,any#3f");
    check_ok("create utf-8,3f:count#lowercase:AsCiI,any#3f", ins != NULL);
    if (ins) {
        out = bsdconv_pack(ins);
        check_str("bsdconv_pack", expect, out ? out : "");
        free(out);
        bsdconv_destroy(ins);
    }

    /* --- test 3-6: upstream api.c phase/codec manipulation assertions --- */
    expect = "utf-8:upper:utf-8,ascii";
    out = bsdconv_insert_phase(in, "upper", INTER, 1);
    check_str("bsdconv_insert_phase", expect, out ? out : "");
    free(in);
    in = out;

    expect = "utf-8:full:utf-8,ascii";
    out = bsdconv_replace_phase(in, "full", INTER, 1);
    check_str("bsdconv_replace_phase", expect, out ? out : "");
    free(in);
    in = out;

    expect = "utf-8:full:utf-8,big5";
    out = bsdconv_replace_codec(in, "big5", 2, 1);
    check_str("bsdconv_replace_codec", expect, out ? out : "");
    free(in);
    in = out;

    expect = "utf-8,ascii:full:utf-8,big5";
    out = bsdconv_insert_codec(in, "ascii", 0, 1);
    check_str("bsdconv_insert_codec", expect, out ? out : "");
    free(in);
    free(out);

    /* --- test 7: end-to-end conversion via bsdconv binary (BSDConv_PATH
     * set by test harness to packaged share/bsdconv). 默认（无参数）即执行
     * 二进制端到端测试；传 "no-binary" 可显式跳过。
     * 注意：README 官方 width 语法为 utf-8:width:（三段式
     * from:inter:to，to 阶段为 null 丢弃输出）；width 的 counter
     * （FULL/HALF）打印到 stderr，管道 grep 前必须 2>&1 合并。 --- */
    if (argc <= 1 || strcmp(argv[1], "no-binary") != 0) {
        int rc = system("printf 'a\\357\\275\\201' | bsdconv utf-8:width:null 2>&1 | grep -q 'FULL: 1'");
        check_ok("end-to-end utf-8:width: via bsdconv binary", rc == 0);
        /* big5 conversion: "中文" in utf-8 -> a4a4 a4e5 in big5.
         * grep -F: 固定字符串匹配（big5 字节序列含非 ASCII，被当正则
         * 解析会在部分环境报 "bad regex"，-F 关闭正则解释）。 */
        rc = system("printf '\\344\\270\\255\\346\\226\\207' | bsdconv utf-8:zhcn:big5 2>/dev/null | grep -Fq \"$(printf '\\244\\244\\244\\345')\"");
        check_ok("end-to-end utf-8:zhcn:big5 via bsdconv binary", rc == 0);
    } else {
        printf("SKIP: end-to-end binary tests (no binary mode)\n");
    }

    printf("\n%s: %d failure(s)\n", failures ? "FAILED" : "ALL PASSED", failures);
    return failures ? 1 : 0;
}
