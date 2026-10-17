/*
 * tinyalsa 2.0.0 —— test_package（消费者视角，层 2）
 *
 * 编译期：安装头 <tinyalsa/asoundlib.h> 可用；运行期：链接已安装的
 * libtinyalsa 并断言纯计算 API 与“不存在声卡”负向路径的行为。
 *
 * 断言数 = 10（assertions_run），与 test_package/MANIFEST.yml 的
 * assertion_count、PR 正文「鸿蒙特有测试」行同源；不进上游用例分母。
 *
 * 输出契约（ctest --output-on-failure 读取）：
 *   ok - <n> <name>       断言通过
 *   not ok - <n> <name>   断言失败
 *   assertions_run=<n> failures=<n>
 */
#include <stdio.h>
#include <string.h>

#include <tinyalsa/asoundlib.h>

static int checks = 0;
static int failures = 0;

static void check(int cond, const char *name, const char *detail)
{
    checks++;
    if (cond) {
        printf("ok - %d %s\n", checks, name);
    } else {
        failures++;
        printf("not ok - %d %s (%s)\n", checks, name, detail ? detail : "");
    }
}

int main(void)
{
    /* 1. 安装的版本头与包版本一致 */
    check(strcmp(TINYALSA_VERSION_STRING, "2.0.0") == 0,
          "version string is 2.0.0", TINYALSA_VERSION_STRING);

    /* 2. TINYALSA_VERSION 数值编码（major<<16 | minor<<8 | patch） */
    check(TINYALSA_VERSION == ((2UL << 16) | (0UL << 8) | 0UL),
          "version numeric macro 2.0.0", "");

    /* 3-6. 纯计算 API：格式 -> 位宽（与上游 tests/src/pcm_test.cc 同期望） */
    check(pcm_format_to_bits(PCM_FORMAT_S16_LE) == 16,
          "pcm_format_to_bits(S16_LE) == 16", "");
    check(pcm_format_to_bits(PCM_FORMAT_S32_LE) == 32,
          "pcm_format_to_bits(S32_LE) == 32", "");
    check(pcm_format_to_bits(PCM_FORMAT_S24_3LE) == 24,
          "pcm_format_to_bits(S24_3LE) == 24", "");
    check(pcm_format_to_bits(PCM_FORMAT_S8) == 8,
          "pcm_format_to_bits(S8) == 8", "");

    /* 7. 空指针安全 API（与上游 mixer_test.cc 同期望） */
    check(strcmp(mixer_ctl_get_type_string(NULL), "") == 0,
          "mixer_ctl_get_type_string(NULL) == \"\"", mixer_ctl_get_type_string(NULL));

    /* 8-10. 不存在的声卡（index 1000）必然是负向路径：该卡号在任何平台
     * 都不存在，因此本组断言与设备在位与否无关。 */
    {
        struct pcm_config config;
        struct pcm *pcm;
        const char *err;

        memset(&config, 0, sizeof(config));
        config.channels = 2;
        config.rate = 48000;
        config.period_size = 1024;
        config.period_count = 4;
        config.format = PCM_FORMAT_S16_LE;

        pcm = pcm_open(1000, 1000, PCM_OUT, &config);
        check(pcm && !pcm_is_ready(pcm),
              "pcm_open(1000,1000) fails on any host", "");

        err = pcm ? pcm_get_error(pcm) : NULL;
        check(err != NULL && err[0] != '\0',
              "pcm_get_error() reports why open failed", err ? err : "(null)");

        check(pcm_close(pcm) == 0, "pcm_close() on failed handle returns 0", "");
    }

    printf("assertions_run=%d failures=%d\n", checks, failures);
    return failures ? 1 : 0;
}
