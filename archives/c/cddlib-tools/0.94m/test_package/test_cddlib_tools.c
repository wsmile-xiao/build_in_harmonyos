/* test_cddlib_tools.c — cddlib-tools 0.94m 消费者真实测试源
 *
 * 实际执行被测包 cddlib-tools 的 cddexec 二进制，对 6 维超立方体的
 * H-表示（12 条半空间不等式）做 --rep 变换，断言输出 V-表示精确为
 * 2^6 = 64 个顶点（可手算的数学结果）。
 *
 * 用法: test_cddlib_tools <cddexec 绝对路径>
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *CUBE6_INE =
    "* 6-dim hypercube\n"
    "H-representation\n"
    "begin\n"
    "    12    7    integer\n"
    " 1  1  0  0  0  0  0\n"
    " 1  0  1  0  0  0  0\n"
    " 1  0  0  1  0  0  0\n"
    " 1  0  0  0  1  0  0\n"
    " 1  0  0  0  0  1  0\n"
    " 1  0  0  0  0  0  1\n"
    " 1 -1  0  0  0  0  0\n"
    " 1  0 -1  0  0  0  0\n"
    " 1  0  0 -1  0  0  0\n"
    " 1  0  0  0 -1  0  0\n"
    " 1  0  0  0  0 -1  0\n"
    " 1  0  0  0  0  0 -1\n"
    "end\n";

static int run_assert(const char *cddexec, const char *indata, const char *outdata) {
    char cmd[4096];
    FILE *fp;

    /* 写 H-表示输入 */
    fp = fopen(indata, "w");
    if (!fp) { fprintf(stderr, "无法创建 %s\n", indata); return 1; }
    fputs(CUBE6_INE, fp);
    fclose(fp);

    /* 实际执行被测二进制: cddexec --rep < in > out */
    snprintf(cmd, sizeof(cmd), "'%s' --rep < '%s' > '%s' 2>&1", cddexec, indata, outdata);
    if (system(cmd) != 0) {
        fprintf(stderr, "cddexec --rep 执行失败: %s\n", cmd);
        return 1;
    }

    /* 读输出并断言 */
    fp = fopen(outdata, "r");
    if (!fp) { fprintf(stderr, "无法读取 %s\n", outdata); return 1; }
    {
        char buf[8192];
        size_t n = fread(buf, 1, sizeof(buf) - 1, fp);
        buf[n] = '\0';
        fclose(fp);
        if (!strstr(buf, "V-representation")) {
            fprintf(stderr, "输出缺少 V-representation\n%s\n", buf);
            return 1;
        }
        if (!strstr(buf, "64 7 real")) {
            fprintf(stderr, "6 维超立方体应有 64 顶点，输出未匹配 '64 7 real'\n%s\n", buf);
            return 1;
        }
    }
    printf("cddlib-tools: 6 维超立方体 H->V 得到 64 个顶点，断言通过\n");
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "用法: %s <cddexec 绝对路径>\n", argv[0]);
        return 2;
    }
    return run_assert(argv[1], "cube6.ine", "cube6.out");
}
