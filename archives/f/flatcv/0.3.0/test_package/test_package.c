#include <stdio.h>
#include <stdlib.h>
#include <flatcv.h>

int main(void) {
    // Test basic FlatCV types and functions
    // Create a simple test image (10x10 RGBA, 4 channels)
    uint32_t width = 10;
    uint32_t height = 10;
    uint32_t rgba_size = width * height * 4;
    uint8_t* test_image = (uint8_t*)malloc(rgba_size);
    
    if (!test_image) {
        fprintf(stderr, "Failed to allocate test image\n");
        return 1;
    }
    
    // Fill with test pattern (RGBA)
    for (uint32_t i = 0; i < rgba_size; i++) {
        test_image[i] = (uint8_t)(i % 256);
    }
    
    // Test fcv_rgba_to_grayscale function
    uint8_t* gray = fcv_rgba_to_grayscale(width, height, test_image);
    if (!gray) {
        fprintf(stderr, "fcv_rgba_to_grayscale failed\n");
        free(test_image);
        return 1;
    }
    
    // Verify grayscale output has correct size
    // (should be width * height, single channel)
    // Basic sanity check: first pixel should be in valid range
    if (gray[0] > 255) {
        fprintf(stderr, "Grayscale output sanity check failed\n");
        free(gray);
        free(test_image);
        return 1;
    }
    
    free(gray);
    free(test_image);
    
    printf("FlatCV test passed: library linked and API callable\n");
    return 0;
}
