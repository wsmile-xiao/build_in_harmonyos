#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STB_IMAGE_RESIZE_IMPLEMENTATION
#include "stb_image_resize2.h"

// 生成测试图像数据（棋盘格模式）
static void generate_test_image(unsigned char *data, int w, int h, int channels) {
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int checker = ((x / 4) + (y / 4)) % 2;
            unsigned char value = checker ? 255 : 64;
            for (int c = 0; c < channels; c++) {
                data[(y * w + x) * channels + c] = value;
            }
        }
    }
}

// 验证输出不是全零或全部相同
static int validate_output(unsigned char *data, int size) {
    if (size < 2) return 0;
    
    int all_same = 1;
    int all_zero = 1;
    unsigned char first = data[0];
    
    for (int i = 0; i < size; i++) {
        if (data[i] != 0) all_zero = 0;
        if (data[i] != first) all_same = 0;
    }
    
    return !all_zero && !all_same;
}

int main(void) {
    int passed = 0;
    int failed = 0;
    
    printf("stb_image_resize2 v2.18 - Comprehensive API Tests\n");
    printf("=================================================\n\n");
    
    // Test 1: 基本 linear resize (downsampling)
    {
        unsigned char input[16 * 16 * 3];
        unsigned char *output;
        generate_test_image(input, 16, 16, 3);
        
        output = stbir_resize_uint8_linear(
            input, 16, 16, 0,
            NULL, 8, 8, 0,
            STBIR_RGB
        );
        
        if (output && validate_output(output, 8 * 8 * 3)) {
            printf("[PASS] Test 1: Basic linear downsampling (16x16 -> 8x8)\n");
            passed++;
            free(output);
        } else {
            printf("[FAIL] Test 1: Basic linear downsampling\n");
            failed++;
            if (output) free(output);
        }
    }
    
    // Test 2: RGBA resize with alpha channel
    {
        unsigned char input[16 * 16 * 4];
        unsigned char *output;
        generate_test_image(input, 16, 16, 4);
        
        output = stbir_resize_uint8_linear(
            input, 16, 16, 0,
            NULL, 8, 8, 0,
            STBIR_RGBA
        );
        
        if (output && validate_output(output, 8 * 8 * 4)) {
            printf("[PASS] Test 2: RGBA resize with alpha channel\n");
            passed++;
            free(output);
        } else {
            printf("[FAIL] Test 2: RGBA resize with alpha channel\n");
            failed++;
            if (output) free(output);
        }
    }
    
    // Test 3: Upsampling (放大)
    {
        unsigned char input[4 * 4 * 3];
        unsigned char *output;
        generate_test_image(input, 4, 4, 3);
        
        output = stbir_resize_uint8_linear(
            input, 4, 4, 0,
            NULL, 12, 12, 0,
            STBIR_RGB
        );
        
        if (output) {
            // Upsampling 会产生插值结果，可能所有像素都相同（如果输入是纯色）
            // 只检查输出非空和非全零
            int all_zero = 1;
            for (int i = 0; i < 12 * 12 * 3; i++) {
                if (output[i] != 0) {
                    all_zero = 0;
                    break;
                }
            }
            if (!all_zero) {
                printf("[PASS] Test 3: Upsampling (4x4 -> 12x12)\n");
                passed++;
            } else {
                printf("[FAIL] Test 3: Upsampling (output is all zero)\n");
                failed++;
            }
            free(output);
        } else {
            printf("[FAIL] Test 3: Upsampling (output is NULL)\n");
            failed++;
        }
    }
    
    // Test 4: sRGB color space resize
    {
        unsigned char input[16 * 16 * 3];
        unsigned char *output;
        generate_test_image(input, 16, 16, 3);
        
        output = stbir_resize_uint8_srgb(
            input, 16, 16, 0,
            NULL, 8, 8, 0,
            STBIR_RGB
        );
        
        if (output && validate_output(output, 8 * 8 * 3)) {
            printf("[PASS] Test 4: sRGB color space resize\n");
            passed++;
            free(output);
        } else {
            printf("[FAIL] Test 4: sRGB color space resize\n");
            failed++;
            if (output) free(output);
        }
    }
    
    // Test 5: 不同边缘模式 (STBIR_EDGE_CLAMP)
    {
        unsigned char input[8 * 8 * 3];
        unsigned char output[16 * 16 * 3];
        generate_test_image(input, 8, 8, 3);
        
        STBIR_RESIZE resize;
        stbir_resize_init(
            &resize,
            input, 8, 8, 0,
            output, 16, 16, 0,
            STBIR_RGB, STBIR_TYPE_UINT8
        );
        stbir_set_edgemodes(&resize, STBIR_EDGE_CLAMP, STBIR_EDGE_CLAMP);
        
        if (stbir_resize_extended(&resize) && validate_output(output, 16 * 16 * 3)) {
            printf("[PASS] Test 5: Edge mode CLAMP\n");
            passed++;
        } else {
            printf("[FAIL] Test 5: Edge mode CLAMP\n");
            failed++;
        }
    }
    
    // Test 6: 自定义滤波器 (MITCHELL filter)
    {
        unsigned char input[16 * 16 * 3];
        unsigned char output[8 * 8 * 3];
        generate_test_image(input, 16, 16, 3);
        
        STBIR_RESIZE resize;
        stbir_resize_init(
            &resize,
            input, 16, 16, 0,
            output, 8, 8, 0,
            STBIR_RGB, STBIR_TYPE_UINT8
        );
        stbir_set_filters(&resize, STBIR_FILTER_MITCHELL, STBIR_FILTER_MITCHELL);
        
        if (stbir_resize_extended(&resize) && validate_output(output, 8 * 8 * 3)) {
            printf("[PASS] Test 6: Mitchell filter\n");
            passed++;
        } else {
            printf("[FAIL] Test 6: Mitchell filter\n");
            failed++;
        }
    }
    
    // Test 7: 预分配输出缓冲区
    {
        unsigned char input[16 * 16 * 3];
        unsigned char output[8 * 8 * 3];
        generate_test_image(input, 16, 16, 3);
        
        unsigned char *result = stbir_resize_uint8_linear(
            input, 16, 16, 0,
            output, 8, 8, 0,
            STBIR_RGB
        );
        
        if (result == output && validate_output(output, 8 * 8 * 3)) {
            printf("[PASS] Test 7: Pre-allocated output buffer\n");
            passed++;
        } else {
            printf("[FAIL] Test 7: Pre-allocated output buffer\n");
            failed++;
        }
    }
    
    printf("\n=================================================\n");
    printf("Test Results: %d passed, %d failed\n", passed, failed);
    
    if (failed > 0) {
        printf("stb_image_resize2 test FAILED\n");
        return 1;
    }
    
    printf("stb_image_resize2 test PASSED\n");
    return 0;
}
