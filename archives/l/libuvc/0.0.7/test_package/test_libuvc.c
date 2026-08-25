/* Consumer smoke test for libuvc.
 *
 * Exercises libuvc APIs that need no USB hardware: the error-string helper,
 * frame allocation, YUYV->BGR frame conversion (pure pixel math in frame.c)
 * and frame release. Conversion output is checked against the values required
 * by the BT.601 arithmetic libuvc implements, so the test verifies the
 * computation rather than merely that the call returned. A negative case
 * asserts an unsupported format is rejected, proving the checks are not
 * vacuously true.
 */
#include <libuvc/libuvc.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* 定点实现允许 ±1 舍入差，超出即判失败。 */
static int near(int actual, int expect)
{
    int diff = actual - expect;
    return diff <= 1 && diff >= -1;
}

/* 构造 2x2 YUYV 帧转 BGR，校验首像素三通道值。失败返回 -1。 */
static int check_convert(const char *name, uint8_t y, uint8_t u, uint8_t v,
                         int eb, int eg, int er)
{
    uint8_t yuyv[8] = { y, u, y, v, y, u, y, v };
    uvc_frame_t in_frame;
    memset(&in_frame, 0, sizeof(in_frame));
    in_frame.data = yuyv;
    in_frame.data_bytes = 8;
    in_frame.width = 2;
    in_frame.height = 2;
    in_frame.frame_format = UVC_FRAME_FORMAT_YUYV;
    in_frame.step = 4;
    in_frame.library_owns_data = 0;

    uvc_frame_t *out_frame = uvc_allocate_frame(12);
    if (out_frame == NULL) {
        fprintf(stderr, "%s: uvc_allocate_frame failed\n", name);
        return -1;
    }

    uvc_error_t ret = uvc_any2bgr(&in_frame, out_frame);
    if (ret != UVC_SUCCESS) {
        uvc_perror(ret, name);
        uvc_free_frame(out_frame);
        return -1;
    }
    if (out_frame->data == NULL || out_frame->data_bytes != 12) {
        fprintf(stderr, "%s: unexpected output size %zu\n", name, out_frame->data_bytes);
        uvc_free_frame(out_frame);
        return -1;
    }

    const uint8_t *px = (const uint8_t *)out_frame->data;
    if (!near(px[0], eb) || !near(px[1], eg) || !near(px[2], er)) {
        fprintf(stderr, "%s: BGR %u,%u,%u != expected %d,%d,%d\n",
                name, px[0], px[1], px[2], eb, eg, er);
        uvc_free_frame(out_frame);
        return -1;
    }
    printf("%s: Y=%u U=%u V=%u -> BGR %u,%u,%u\n", name, y, u, v, px[0], px[1], px[2]);
    uvc_free_frame(out_frame);
    return 0;
}

int main(void)
{
    /* 1. uvc_strerror 必须返回非空字符串（纯查表，无需硬件）。 */
    const char *err = uvc_strerror(UVC_ERROR_TIMEOUT);
    if (err == NULL || err[0] == '\0') {
        fprintf(stderr, "uvc_strerror(UVC_ERROR_TIMEOUT) returned empty\n");
        return 1;
    }
    printf("uvc_strerror(UVC_ERROR_TIMEOUT) = %s\n", err);

    /* 2-4. 中性色度下 BGR 等于亮度本身，并随亮度线性变化。 */
    if (check_convert("neutral", 149, 128, 128, 149, 149, 149) != 0) return 2;
    if (check_convert("bright", 200, 128, 128, 200, 200, 200) != 0) return 3;
    if (check_convert("dark", 50, 128, 128, 50, 50, 50) != 0) return 4;

    /* 5. 带色度分量：B 上溢饱和到 255，G/R 按 BT.601 系数偏移。 */
    if (check_convert("chroma", 149, 200, 100, 255, 144, 109) != 0) return 5;

    /* 6. 反证：不支持的格式必须被拒绝，确保上述断言不是恒真。 */
    uint8_t raw[8] = { 0 };
    uvc_frame_t bad_frame;
    memset(&bad_frame, 0, sizeof(bad_frame));
    bad_frame.data = raw;
    bad_frame.data_bytes = 8;
    bad_frame.width = 2;
    bad_frame.height = 2;
    bad_frame.frame_format = UVC_FRAME_FORMAT_UNKNOWN;
    bad_frame.step = 4;

    uvc_frame_t *rejected = uvc_allocate_frame(12);
    if (rejected == NULL) {
        fprintf(stderr, "uvc_allocate_frame failed for negative case\n");
        return 6;
    }
    uvc_error_t bad_ret = uvc_any2bgr(&bad_frame, rejected);
    uvc_free_frame(rejected);
    if (bad_ret == UVC_SUCCESS) {
        fprintf(stderr, "unsupported frame format was not rejected\n");
        return 6;
    }
    printf("unsupported format rejected with %d (%s)\n", (int)bad_ret, uvc_strerror(bad_ret));

    printf("libuvc consumer smoke passed\n");
    return 0;
}
