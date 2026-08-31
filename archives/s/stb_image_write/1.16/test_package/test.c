#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    // Get writable temp directory (OHOS: /tmp is read-only, use TMPDIR)
    const char *tmpdir = getenv("TMPDIR");
    if (!tmpdir) tmpdir = getenv("HOME");
    if (!tmpdir) tmpdir = ".";
    
    char png_path[256], bmp_path[256], tga_path[256], jpg_path[256];
    snprintf(png_path, sizeof(png_path), "%s/test_output.png", tmpdir);
    snprintf(bmp_path, sizeof(bmp_path), "%s/test_output.bmp", tmpdir);
    snprintf(tga_path, sizeof(tga_path), "%s/test_output.tga", tmpdir);
    snprintf(jpg_path, sizeof(jpg_path), "%s/test_output.jpg", tmpdir);
    
    // Create a simple 4x4 RGB test image (red gradient)
    unsigned char img[4*4*3];
    int i;
    
    for (i = 0; i < 4*4; i++) {
        img[i*3 + 0] = (unsigned char)(i * 16);  // Red gradient
        img[i*3 + 1] = 0;                         // No green
        img[i*3 + 2] = 0;                         // No blue
    }
    
    // Test PNG writing
    int result = stbi_write_png(png_path, 4, 4, 3, img, 4*3);
    if (!result) {
        fprintf(stderr, "Failed to write PNG to %s\n", png_path);
        return 1;
    }
    
    // Test BMP writing
    result = stbi_write_bmp(bmp_path, 4, 4, 3, img);
    if (!result) {
        fprintf(stderr, "Failed to write BMP to %s\n", bmp_path);
        return 1;
    }
    
    // Test TGA writing
    result = stbi_write_tga(tga_path, 4, 4, 3, img);
    if (!result) {
        fprintf(stderr, "Failed to write TGA to %s\n", tga_path);
        return 1;
    }
    
    // Test JPEG writing
    result = stbi_write_jpg(jpg_path, 4, 4, 3, img, 90);
    if (!result) {
        fprintf(stderr, "Failed to write JPEG to %s\n", jpg_path);
        return 1;
    }
    
    printf("stb_image_write 1.16: All image formats written successfully\n");
    printf("  PNG: %s\n", png_path);
    printf("  BMP: %s\n", bmp_path);
    printf("  TGA: %s\n", tga_path);
    printf("  JPEG: %s\n", jpg_path);
    return 0;
}
