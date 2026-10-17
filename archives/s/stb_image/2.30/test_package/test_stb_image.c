#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

/* 简单的 1x1 PNG 图像数据（红色像素） */
static const unsigned char png_data[] = {
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0x00, 0x00, 0x00, 0x0d,
    0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xde, 0x00, 0x00, 0x00,
    0x0c, 0x49, 0x44, 0x41, 0x54, 0x08, 0xd7, 0x63, 0xf8, 0xcf, 0xc0, 0x00,
    0x00, 0x03, 0x01, 0x01, 0x00, 0x18, 0xdd, 0x8d, 0xb4, 0x00, 0x00, 0x00,
    0x00, 0x49, 0x45, 0x4e, 0x44, 0xae, 0x42, 0x60, 0x82
};

/* 简单的 1x1 BMP 图像数据（蓝色像素） */
static const unsigned char bmp_data[] = {
    0x42, 0x4d, 0x3a, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x36, 0x00,
    0x00, 0x00, 0x28, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x18, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0x00, 0x00, 0x00
};

int main(void)
{
    int width, height, channels;
    unsigned char *img;
    
    printf("Testing stb_image 2.30...\n");
    
    /* 测试 1: 从内存加载 PNG */
    img = stbi_load_from_memory(png_data, sizeof(png_data), &width, &height, &channels, 0);
    if (!img) {
        fprintf(stderr, "Failed to load PNG from memory: %s\n", stbi_failure_reason());
        return 1;
    }
    printf("✓ PNG: loaded %dx%d image with %d channels\n", width, height, channels);
    if (width != 1 || height != 1) {
        fprintf(stderr, "PNG: unexpected dimensions %dx%d (expected 1x1)\n", width, height);
        stbi_image_free(img);
        return 1;
    }
    stbi_image_free(img);
    
    /* 测试 2: 从内存加载 BMP */
    img = stbi_load_from_memory(bmp_data, sizeof(bmp_data), &width, &height, &channels, 0);
    if (!img) {
        fprintf(stderr, "Failed to load BMP from memory: %s\n", stbi_failure_reason());
        return 1;
    }
    printf("✓ BMP: loaded %dx%d image with %d channels\n", width, height, channels);
    if (width != 1 || height != 1) {
        fprintf(stderr, "BMP: unexpected dimensions %dx%d (expected 1x1)\n", width, height);
        stbi_image_free(img);
        return 1;
    }
    stbi_image_free(img);
    
    /* 测试 3: info 查询（PNG） */
    if (!stbi_info_from_memory(png_data, sizeof(png_data), &width, &height, &channels)) {
        fprintf(stderr, "Failed to get PNG info: %s\n", stbi_failure_reason());
        return 1;
    }
    printf("✓ PNG info: %dx%d, %d channels\n", width, height, channels);
    
    /* 测试 4: 错误处理 */
    const unsigned char bad_data[] = {0x00, 0x01, 0x02, 0x03};
    img = stbi_load_from_memory(bad_data, sizeof(bad_data), &width, &height, &channels, 0);
    if (img) {
        fprintf(stderr, "Should have failed to load invalid data\n");
        stbi_image_free(img);
        return 1;
    }
    printf("✓ Error handling works: %s\n", stbi_failure_reason());
    
    printf("\n✅ All tests passed!\n");
    return 0;
}
