/* 鸿蒙消费者用例 — liquid 1.7.0
 *
 * 以 resamp_crcf（分数速率重采样）为实际应用场景，
 * 构造输入样本流 → 逐样本调用 resamp_crcf_execute 重采样 →
 * 校验实际输出样本数与 resamp_crcf_get_num_output 预测一致。
 *
 * 在鸿蒙设备上，需要先确保 LD_LIBRARY_PATH 含 libliquid.so 所在目录
 * （conanrun 环境会自动注入）。
 */
#include <stdio.h>
#include <stdlib.h>
#include <complex.h>
#include <math.h>
#include <liquid/liquid.h>

int main(void)
{
    /* 重采样率 0.12345 (任意合理值) */
    float rate = 0.12345f;
    void *q = resamp_crcf_create(rate, 12, 0.25f, 60.0f, 256);
    if (q == NULL) {
        fprintf(stderr, "FAIL: resamp_crcf_create returned NULL\n");
        return 1;
    }

    /* 打印对象内部参数，验证函数符号全部可用 */
    resamp_crcf_print(q);

    /* 逐样本执行重采样，统计实际输出样本数 */
    unsigned int num_input = 1000;
    liquid_float_complex input_sample;
    liquid_float_complex output_sample;
    unsigned int num_written_total = 0;
    unsigned int num_written;
    int rc;

    for (unsigned int i = 0; i < num_input; i++) {
        /* 构造确定性输入样本：实部 = i*0.001，虚部 = 0 */
        input_sample = (liquid_float_complex)((float)i * 0.001f);
        rc = resamp_crcf_execute(q, input_sample, &output_sample, &num_written);
        if (rc != 0) {
            fprintf(stderr, "FAIL: resamp_crcf_execute returned %d at i=%u\n",
                    rc, i);
            resamp_crcf_destroy(q);
            return 1;
        }
        num_written_total += num_written;
    }

    /* 校验：实际输出数接近 rate*n_input（±2 容差，涵盖滤波器延迟） */
    float expected_f = rate * (float)num_input;
    int delta = (int)num_written_total - (int)roundf(expected_f);

    /* 校验：resamp_crcf_get_num_output 预测值在实测值 ±2 内（API 一致性） */
    unsigned int api_expected = resamp_crcf_get_num_output(q, num_input);

    printf("resamp: %u input -> %u output (rate*n_input=%.1f, api_expected=%u, delta=%d)\n",
           num_input, num_written_total, expected_f, api_expected, delta);

    if (num_written_total == 0) {
        fprintf(stderr, "FAIL: no output samples produced\n");
        resamp_crcf_destroy(q);
        return 1;
    }

    if (delta < -2 || delta > 2) {
        fprintf(stderr,
                "FAIL: output count %u far from rate*n_input (%.1f, delta=%d)\n",
                num_written_total, expected_f, delta);
        resamp_crcf_destroy(q);
        return 1;
    }

    int api_delta = (int)num_written_total - (int)api_expected;
    if (api_delta < -2 || api_delta > 2) {
        fprintf(stderr,
                "FAIL: get_num_output prediction %u diverged from actual %u\n",
                api_expected, num_written_total);
        resamp_crcf_destroy(q);
        return 1;
    }

    resamp_crcf_destroy(q);
    printf("liquid ohos consumer PASS\n");
    return 0;
}
