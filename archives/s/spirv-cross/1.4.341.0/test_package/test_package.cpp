#include <cstdint>
#include <stdio.h>
#include <string.h>

#include <spirv_cross/spirv_cross_c.h>

static const SpvId kMinimalComputeShader[] = {
    0x07230203, 0x00010000, 0, 5, 0,
    0x00020011, 1,
    0x0003000e, 0, 1,
    0x0005000f, 5, 3, 0x6e69616d, 0,
    0x00060010, 3, 17, 1, 1, 1,
    0x00030003, 2, 450,
    0x00020013, 1,
    0x00030021, 2, 1,
    0x00050036, 1, 3, 0, 2,
    0x000200f8, 4,
    0x000100fd,
    0x00010038,
};

int main(void) {
    spvc_context context = NULL;
    spvc_parsed_ir ir = NULL;
    spvc_compiler compiler = NULL;
    const char *source = NULL;
    FILE *module_file = NULL;

    if (spvc_context_create(&context) != SPVC_SUCCESS || context == NULL) {
        return 1;
    }
    if (spvc_context_parse_spirv(context, kMinimalComputeShader,
                                 sizeof(kMinimalComputeShader) / sizeof(kMinimalComputeShader[0]),
                                 &ir) != SPVC_SUCCESS) {
        spvc_context_destroy(context);
        return 2;
    }
    if (spvc_context_create_compiler(context, SPVC_BACKEND_GLSL, ir,
                                     SPVC_CAPTURE_MODE_TAKE_OWNERSHIP,
                                     &compiler) != SPVC_SUCCESS) {
        spvc_context_destroy(context);
        return 3;
    }
    if (spvc_compiler_compile(compiler, &source) != SPVC_SUCCESS ||
        source == NULL || strstr(source, "void main") == NULL) {
        spvc_context_destroy(context);
        return 4;
    }

    module_file = fopen("minimal.spv", "wb");
    if (module_file == NULL ||
        fwrite(kMinimalComputeShader, sizeof(kMinimalComputeShader), 1, module_file) != 1) {
        if (module_file != NULL) {
            fclose(module_file);
        }
        spvc_context_destroy(context);
        return 5;
    }
    fclose(module_file);
    printf("SPIRV-Cross C API generated:\n%s\n", source);
    spvc_context_destroy(context);
    return 0;
}
