#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define QOA_IMPLEMENTATION
#include "qoa.h"

static int g_failures = 0;

#define CHECK(cond, msg) \
    do { \
        if (cond) { \
            printf("  [PASS] %s\n", msg); \
        } else { \
            printf("  [FAIL] %s\n", msg); \
            g_failures++; \
        } \
    } while (0)

#define N_SAMPLES 9600
#define SAMPLE_RATE 48000
#define AMPLITUDE 12000.0
/* QOA 为有损压缩；对平滑正弦信号量化误差远小于该容差，
 * 但足以捕获整体失效（如全零/错位解码）。 */
#define TOLERANCE 2048

static double max_err_vs(const short *a, const short *b, unsigned int n)
{
    double max_err = 0.0;
    unsigned int i;
    for (i = 0; i < n; i++) {
        double err = fabs((double)a[i] - (double)b[i]);
        if (err > max_err) {
            max_err = err;
        }
    }
    return max_err;
}

int main(void)
{
    short samples[N_SAMPLES];
    unsigned char *encoded = NULL;
    short *decoded = NULL;
    short *re_read = NULL;
    qoa_desc qoa;
    qoa_desc out;
    qoa_desc rd;
    unsigned int encoded_len = 0;
    unsigned int raw_len = (unsigned int)sizeof(samples);
    unsigned int i;
    const char *tmp_path = "test_qoa_roundtrip.qoa";

    printf("qoa 0-git20251017 OHOS test\n");

    /* 1 通道平滑正弦（上、下半振幅），头尾淡入避免编码边界失真 */
    for (i = 0; i < N_SAMPLES; i++) {
        double t = (double)i / (double)SAMPLE_RATE;
        double env = (i < 64) ? ((double)i / 64.0) : 1.0;
        samples[i] = (short)(AMPLITUDE * env * sin(2.0 * 3.14159265358979323846 * 220.0 * t));
    }

    memset(&qoa, 0, sizeof(qoa));
    qoa.channels = 1;
    qoa.samplerate = SAMPLE_RATE;
    qoa.samples = N_SAMPLES;

    encoded = (unsigned char *)qoa_encode(samples, &qoa, &encoded_len);
    CHECK(encoded != NULL, "qoa_encode returns buffer");
    CHECK(encoded && memcmp(encoded, "qoaf", 4) == 0,
          "encoded file magic is 'qoaf'");
    CHECK(encoded_len >= QOA_MIN_FILESIZE,
          "encoded length >= QOA_MIN_FILESIZE");
    CHECK(encoded_len < raw_len / 2,
          "encoded size < raw/2 (compression effective)");
    printf("    encoded=%u raw=%u\n", encoded_len, raw_len);

    memset(&out, 0, sizeof(out));
    decoded = qoa_decode(encoded, (int)encoded_len, &out);
    CHECK(decoded != NULL, "qoa_decode returns buffer");
    CHECK(out.channels == 1, "decoded channels is 1");
    CHECK(out.samplerate == SAMPLE_RATE, "decoded samplerate is 48000");
    CHECK(out.samples == N_SAMPLES, "decoded samples count matches");
    CHECK(decoded && max_err_vs(samples, decoded, N_SAMPLES) <= TOLERANCE,
          "decoded max abs error <= tolerance (lossy but bounded)");
    printf("    max_err=%.0f\n",
           decoded ? max_err_vs(samples, decoded, N_SAMPLES) : -1.0);

    /* stdio 路径：qoa_write / qoa_read 往返（QOA_NO_STDIO 未定义） */
    CHECK(qoa_write(tmp_path, samples, &qoa) > 0, "qoa_write succeeds");
    re_read = (short *)qoa_read(tmp_path, &rd);
    CHECK(re_read != NULL, "qoa_read returns buffer");
    CHECK(rd.channels == 1 && rd.samplerate == SAMPLE_RATE &&
              rd.samples == N_SAMPLES,
          "re-read desc matches");
    CHECK(re_read && max_err_vs(samples, re_read, N_SAMPLES) <= TOLERANCE,
          "re-read samples within tolerance");

    free(encoded);
    free(decoded);
    free(re_read);
    remove(tmp_path);

    if (g_failures == 0) {
        printf("HMBS_TEST_PACKAGE_RESULT: PASS\n");
        return 0;
    }
    printf("HMBS_TEST_PACKAGE_RESULT: FAIL (%d)\n", g_failures);
    return 1;
}
