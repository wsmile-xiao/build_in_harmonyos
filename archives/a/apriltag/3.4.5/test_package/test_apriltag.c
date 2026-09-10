/* apriltag 3.4.5 — 消费者测试（真实调用公开 C API）
 *
 * 链接 libapriltag 并走一遍检测器全流程：
 *   1) matd（common 数学库）确定性数值断言 —— 编译期即验证头闭包
 *      （apriltag.h 相对 include common/*.h，install 布局必须保目录）；
 *   2) tag36h11 family 结构字段断言（nbits==36, h==11, ncodes>0）；
 *   3) detector create / add_family_bits / detect / destroy 生命周期，
 *      全白图（无梯度/无四边形）上 detect 必须返回 0 个检测 —— 走完整
 *      四线检测+解码管线且结果确定。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "apriltag.h"
#include "tag36h11.h"
#include "common/matd.h"
#include "common/image_u8.h"

static int failures = 0;

static void check(int cond, const char *what) {
    if (!cond) {
        fprintf(stderr, "FAIL: %s\n", what);
        failures++;
    }
}

int main(void) {
    /* 1) matd 数学：转置数值 */
    matd_t *a = matd_create(2, 2);
    matd_put(a, 0, 0, 1.0);
    matd_put(a, 0, 1, 2.0);
    matd_put(a, 1, 0, 3.0);
    matd_put(a, 1, 1, 4.0);
    matd_t *at = matd_transpose(a);
    check(matd_get(at, 0, 1) == 3.0, "matd_transpose [0][1]==3.0");
    check(matd_get(at, 1, 0) == 2.0, "matd_transpose [1][0]==2.0");
    matd_t *d2 = matd_scale(at, 2.0);
    check(matd_get(d2, 0, 0) == 2.0, "matd_scale [0][0]==2.0");
    matd_destroy(d2);
    matd_destroy(at);
    matd_destroy(a);

    /* 2) tag36h11 family 结构字段 */
    apriltag_family_t *tf = tag36h11_create();
    check(tf != NULL, "tag36h11_create non-NULL");
    check(tf->nbits == 36, "tag36h11 nbits==36");
    check(tf->h == 11, "tag36h11 h==11");
    check(tf->ncodes > 0, "tag36h11 ncodes>0");
    check(tf->width_at_border > 0 && tf->total_width > 0, "tag36h11 geometry sane");

    /* 3) 检测器生命周期 + 全白图 detect == 0 */
    apriltag_detector_t *td = apriltag_detector_create();
    check(td != NULL, "apriltag_detector_create non-NULL");
    apriltag_detector_add_family_bits(td, tf, 2);

    image_u8_t *im = image_u8_create(128, 128);
    memset(im->buf, 255, (size_t)im->stride * (size_t)im->height);

    zarray_t *dets = apriltag_detector_detect(td, im);
    check(dets != NULL, "detect returned zarray");
    check(zarray_size(dets) == 0, "blank image -> 0 detections");

    apriltag_detections_destroy(dets);
    image_u8_destroy(im);
    apriltag_detector_destroy(td);
    tag36h11_destroy(tf);

    if (failures) {
        printf("apriltag consumer test: %d FAILURES\n", failures);
        return 1;
    }
    printf("apriltag consumer test OK (matd=3 family=4 detector-blank=2, all passed)\n");
    return 0;
}
