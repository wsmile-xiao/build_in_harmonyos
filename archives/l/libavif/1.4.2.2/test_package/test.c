/* libavif 1.4.2 —— 真实 API 验证，重点是**确认 dav1d 解码后端真的接上了**。
 *
 * 判据设计：
 *   ① avifVersion() 与本包版本一致；
 *   ② **avifCodecName(AUTO, CAN_DECODE) 必须返回 "dav1d"** —— 这条最关键：
 *      配方用 `-DAVIF_CODEC_DAV1D=SYSTEM` 接的后端，只有真接上了这里才报 dav1d；
 *      若后端没接上，libavif 照样能编能链，但**运行期一张 AVIF 也解不了**——
 *      正是那种「构建成功、消费方才发现不能用」的缺陷；
 *   ③ 编码后端应报「无」：本包按参考构建关掉了 aom（鸿蒙 pillow 的 wheel 只链 dav1d），
 *      这条把「配置符合预期」也钉住，防止将来有人误开 aom 而无人察觉；
 *   ④ avifImageCreate/Destroy 真实分配释放一张图。
 *
 * 头路径查过上游 include/ 实际布局：<avif/avif.h>。
 */
#include <avif/avif.h>

#include <stdio.h>
#include <string.h>

static int failures = 0;
#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            fprintf(stderr, "[FAIL] %s  (%s:%d)\n", (msg), __FILE__, __LINE__);\
            ++failures;                                                        \
        } else {                                                               \
            printf("[ok] %s\n", (msg));                                        \
        }                                                                      \
    } while (0)

int main(void) {
    const char *ver = avifVersion();
    printf("     libavif 版本: %s\n", ver ? ver : "(null)");
    CHECK(ver != NULL && strncmp(ver, "1.4.2", 5) == 0, "avifVersion() == 1.4.2");

    const char *dec = avifCodecName(AVIF_CODEC_CHOICE_AUTO, AVIF_CODEC_FLAG_CAN_DECODE);
    printf("     解码后端: %s\n", dec ? dec : "(无)");
    CHECK(dec != NULL && strcmp(dec, "dav1d") == 0,
          "解码后端是 dav1d（证明 AVIF_CODEC_DAV1D=SYSTEM 真接上了）");

    const char *enc = avifCodecName(AVIF_CODEC_CHOICE_AUTO, AVIF_CODEC_FLAG_CAN_ENCODE);
    printf("     编码后端: %s\n", enc ? enc : "(无)");
    CHECK(enc == NULL,
          "无编码后端（本包按参考构建关掉 aom：鸿蒙 pillow 的 wheel 只链 dav1d）");

    avifImage *img = avifImageCreate(64, 32, 8, AVIF_PIXEL_FORMAT_YUV420);
    CHECK(img != NULL, "avifImageCreate() 成功");
    if (img) {
        CHECK(img->width == 64 && img->height == 32, "图像尺寸为 64x32");
        CHECK(img->depth == 8, "位深为 8");
        avifImageDestroy(img);
        printf("[ok] avifImageDestroy() 未崩溃\n");
    }

    if (failures) {
        fprintf(stderr, "\nlibavif: %d 项断言失败\n", failures);
        return 1;
    }
    printf("\nlibavif 1.4.2: 全部断言通过\n");
    return 0;
}
