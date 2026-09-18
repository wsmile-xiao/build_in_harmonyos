/*
 * ssdeep 2.8 HarmonyOS 专项测试（作为交付物随 test_package 提交，9 项断言）
 * 验证 fuzzy hashing 库在 OHOS 平台上的核心行为：
 *   1) fuzzy_hash_buf / fuzzy_hash_filename 确定性（同输入必同摘要）
 *   2) fuzzy_compare 相似度：相同内容 score=100，近似内容高分（>0），无关内容 score=0
 *   3) CLI（ssdeep）管线：文件 -> hash 输出包含被哈希文件名且非空
 * 仅使用安装产物的公开头文件 fuzzy.h 与公开 API。
 *
 * 用法：test_ssdeep_ohos [ssdeep_cli_path]
 *   argv[1] 为 ssdeep CLI 可执行文件路径（conan test_package 通过
 *   CMake/CTest 注入被测包 bin/ssdeep）；省略时使用 "ssdeep"（PATH 查找）。
 *   输入文件写入当前工作目录（相对路径），不依赖任何绝对路径。
 *
 * 注意（上游算法语义）：fuzzy_compare 基于编辑距离 + SPAMSUM 长度缩放，
 * 短/重复内容会被 eliminate_sequences 削短导致相同摘要也得不到 100，
 * 因此本项目采用内容丰富输入（8KB 伪随机）验证其真实语义。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "fuzzy.h"

#define BUF_SIZE 8192
#define INPUT_FILE "ohos-test-input.bin"

static int failures = 0;

static void check(int cond, const char *msg)
{
    if (cond) {
        printf("  [PASS] %s\n", msg);
    } else {
        printf("  [FAIL] %s\n", msg);
        failures++;
    }
}

static void fill_random(unsigned char *buf, size_t n, unsigned seed)
{
    /* 简单 LCG，保持可复现 */
    unsigned s = seed;
    size_t i;
    for (i = 0; i < n; i++) {
        s = s * 1103515245u + 12345u;
        buf[i] = (unsigned char)((s >> 16) & 0xff);
    }
}

int main(int argc, char **argv)
{
    char buf[BUF_SIZE + 512];
    char buf2[BUF_SIZE + 512];
    char buf3[BUF_SIZE + 512];
    unsigned char data[BUF_SIZE];
    unsigned char perturbed[BUF_SIZE];
    unsigned char unrelated[BUF_SIZE];
    const char *cli_bin = (argc > 1 && argv[1][0]) ? argv[1] : "ssdeep";
    int rc, score;
    FILE *fp;

    printf("== ssdeep 2.8 HarmonyOS 专项测试 ==\n");
    printf("  CLI: %s\n", cli_bin);
#if defined(__OHOS__) || defined(__OHOS)
    printf("  (compiled with __OHOS__ macro)\n");
#endif

    fill_random(data, BUF_SIZE, 42);

    /*
     * 断言 1/9：fuzzy_hash_buf 返回成功且摘要非空
     * 断言 2/9：同内容两次哈希结果完全一致（确定性）
     */
    rc = fuzzy_hash_buf(data, BUF_SIZE, buf);
    check(rc == 0 && strlen(buf) > 0, "fuzzy_hash_buf 返回成功且摘要非空");
    rc = fuzzy_hash_buf(data, BUF_SIZE, buf2);
    check(rc == 0 && strcmp(buf, buf2) == 0, "同内容两次哈希结果完全一致（确定性）");

    /* 断言 3/9：文件哈希与 buffer 哈希一致（相对路径，当前工作目录） */
    fp = fopen(INPUT_FILE, "wb");
    if (fp) {
        fwrite(data, 1, BUF_SIZE, fp);
        fclose(fp);
    }
    rc = fuzzy_hash_filename(INPUT_FILE, buf3);
    check(rc == 0 && strcmp(buf, buf3) == 0, "fuzzy_hash_filename 与 fuzzy_hash_buf 摘要一致");

    /*
     * 断言 4/9：相同摘要 fuzzy_compare 得分 = 100
     * 断言 5-8/9：相似度语义（内容丰富输入）：单字节扰动 -> 高分(>0)；无关内容 -> 0
     */
    score = fuzzy_compare(buf, buf2);
    printf("  相同摘要实际得分 = %d\n", score);
    check(score == 100, "相同摘要 fuzzy_compare 得分 = 100");

    memcpy(perturbed, data, BUF_SIZE);
    perturbed[BUF_SIZE / 2] ^= 0x55;   /* 单字节扰动 */
    char near_hash[BUF_SIZE + 512];
    rc = fuzzy_hash_buf(perturbed, BUF_SIZE, near_hash);
    check(rc == 0, "近似内容哈希成功");
    score = fuzzy_compare(buf, near_hash);
    printf("  近似内容相似度得分 = %d\n", score);
    check(score > 0, "近似内容得分 > 0（模糊哈希特性）");

    fill_random(unrelated, BUF_SIZE, 2026);
    char unrel_hash[BUF_SIZE + 512];
    rc = fuzzy_hash_buf(unrelated, BUF_SIZE, unrel_hash);
    check(rc == 0, "无关内容哈希成功");
    score = fuzzy_compare(buf, unrel_hash);
    printf("  无关内容相似度得分 = %d\n", score);
    check(score == 0, "无关内容得分 = 0");

    /* 断言 9/9：CLI 管线一致性：ssdeep <file> 输出含被哈希文件名且非空 */
    char cmd[2048];
    char cli_out[1024] = {0};
    snprintf(cmd, sizeof(cmd), "\"%s\" \"%s\" 2>/dev/null", cli_bin, INPUT_FILE);
    FILE *cli = popen(cmd, "r");
    if (cli) {
        size_t n = fread(cli_out, 1, sizeof(cli_out) - 1, cli);
        cli_out[n] = '\0';
        pclose(cli);
    }
    check(strlen(cli_out) > 0 && strstr(cli_out, INPUT_FILE),
          "CLI ssdeep 输出包含被哈希文件名（管线可用）");

    printf("\n== 结果: %s (%d failure%s) ==\n",
           failures == 0 ? "全部通过" : "存在失败",
           failures, failures == 1 ? "" : "s");
    remove(INPUT_FILE);
    return failures == 0 ? 0 : 1;
}