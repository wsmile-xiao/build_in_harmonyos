// test_package consumer test — libfacedetection 3.0
// 真实调用库 API：构造一张小尺寸 BGR 图像，调用 facedetect_cnn 完成一次
// 人脸检测推理，验证头文件/链接/API 契约在目标平台可用（R34：非空壳测试）。
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 库 API：结果缓冲区必须 ≥ 0x20000 字节
#include "facedetection/facedetectcnn.h"
#define DETECT_BUFFER_SIZE 0x20000

int main(void) {
    // 256x192 BGR 图像（纯黑背景，无真实人脸 → 期望 0 张人脸，但 API 必须正常返回）
    const int width = 256;
    const int height = 192;
    const int step = width * 3;
    unsigned char *image = (unsigned char *)malloc((size_t)width * height * 3);
    unsigned char *pBuffer = (unsigned char *)malloc(DETECT_BUFFER_SIZE);
    if (!image || !pBuffer) {
        fprintf(stderr, "FAIL: alloc image/buffer failed\n");
        free(image);
        free(pBuffer);
        return 1;
    }
    memset(image, 0, (size_t)width * height * 3);

    int *pResults = facedetect_cnn(pBuffer, image, width, height, step);
    if (pResults == NULL) {
        fprintf(stderr, "FAIL: facedetect_cnn returned NULL\n");
        free(image);
        free(pBuffer);
        return 1;
    }
    int faces = *pResults;
    if (faces < 0) {
        fprintf(stderr, "FAIL: facedetect_cnn returned negative count %d\n", faces);
        free(image);
        free(pBuffer);
        return 1;
    }
    printf("PASS: libfacedetection 3.0 API OK, %d faces detected (blank image)\n", faces);

    free(image);
    free(pBuffer);
    return 0;
}
