/* test_package consumer test for pajeng 1.3.10
 * 1) 以库使用者身份链接 libpaje，构造 PajeColor 对并校验公开字段；
 * 2) 运行包内 pj_dump 工具解析随包 trace 样本，断言退出码与输出。 */
#include <cstdio>
#include <cstdlib>
#include <string>

#include "PajeColor.h"

static const char *kTraceFile = TRACE_FILE;
static const char *kPjDumpBin = PJ_DUMP_BIN;

int main(void) {
    /* 1) 公开 API：PajeColor 构造与字段校验（真实链接 libpaje） */
    PajeColor color(0.25f, 0.5f, 0.75f, 1.0f);
    if (color.r != 0.25f || color.g != 0.5f ||
        color.b != 0.75f || color.a != 1.0f) {
        fprintf(stderr, "FAIL: PajeColor fields mismatch: %f %f %f %f\n",
                color.r, color.g, color.b, color.a);
        return 1;
    }

    /* 2) 行为断言：pj_dump 解析 trace 必须成功且产出 Container 行 */
    if (!kPjDumpBin || !kTraceFile) {
        fprintf(stderr, "FAIL: PJ_DUMP_BIN/TRACE_FILE not provided\n");
        return 2;
    }
    std::string cmd = std::string(kPjDumpBin) + " " + kTraceFile;
    FILE *p = popen(cmd.c_str(), "r");
    if (!p) {
        fprintf(stderr, "FAIL: popen(%s)\n", cmd.c_str());
        return 1;
    }
    std::string out;
    char buf[512];
    while (fgets(buf, sizeof(buf), p))
        out += buf;
    int rc = pclose(p);
    if (rc != 0) {
        fprintf(stderr, "FAIL: pj_dump exited %d\n", rc);
        return 1;
    }
    if (out.find("Container") == std::string::npos) {
        fprintf(stderr, "FAIL: pj_dump output lacks Container rows:\n%s\n",
                out.c_str());
        return 1;
    }

    printf("pajeng consumer test OK: PajeColor fields verified; "
           "pj_dump output %zu bytes with Container rows\n", out.size());
    return 0;
}
