// test_cimg.cpp — CImg header-only 库消费者测试
// 验证 CImg.h 可被正确 include 和编译，核心图像处理 API 可用
// 禁用 X11 显示功能（cimg_display=0），纯计算测试
#define cimg_display 0

#include "CImg.h"
#include <cstdio>

int main() {
    using namespace cimg_library;

    // 测试1: 创建图像并验证尺寸
    CImg<float> img(100, 100, 1, 3, 0);  // 100x100 RGB 图像
    if (img.width() != 100 || img.height() != 100 || img.spectrum() != 3) {
        std::printf("FAIL: image dimensions mismatch\n");
        return 1;
    }

    // 测试2: 填充和像素访问
    img.fill(128.0f);
    if (img(0, 0, 0, 0) != 128.0f || img(99, 99, 0, 2) != 128.0f) {
        std::printf("FAIL: pixel value mismatch\n");
        return 1;
    }

    // 测试3: 算术运算（图像加法）
    CImg<float> result = img + img;
    if (result(50, 50, 0, 1) != 256.0f) {
        std::printf("FAIL: arithmetic result mismatch\n");
        return 1;
    }

    // 测试4: 高斯模糊（纯计算，不涉及显示）
    CImg<float> blurred = img.get_blur(2.0f);
    if (blurred.width() != 100 || blurred.height() != 100) {
        std::printf("FAIL: blur output dimensions mismatch\n");
        return 1;
    }

    // 测试5: CImgList 操作
    CImgList<float> list;
    list.insert(img);
    list.insert(result);
    if (list.size() != 2) {
        std::printf("FAIL: list size mismatch\n");
        return 1;
    }

    std::printf("PASS: all CImg tests passed\n");
    return 0;
}
