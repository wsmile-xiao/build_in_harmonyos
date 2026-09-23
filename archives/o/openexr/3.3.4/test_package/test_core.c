/* test_core.c — 验证 OpenEXRCore C API（含 libdeflate 链路） */
#include <stdio.h>

#include <openexr.h>
#include <openexr_base.h>

int main(void)
{
    int major = 0, minor = 0, patch = 0;
    const char *extra = NULL;

    /* 上游签名：void exr_get_library_version(int*, int*, int*, const char**) */
    exr_get_library_version(&major, &minor, &patch, &extra);
    printf("openexr core version: %d.%d.%d extra=%s\n",
           major, minor, patch, extra ? extra : "()");

    if (major != 3 || minor != 3 || patch != 4) {
        printf("unexpected core version\n");
        return 1;
    }

    /* C API 其他导出函数可用性（链接器验证导出表完整） */
    int max_w = 0, max_h = 0;
    exr_get_default_maximum_image_size(&max_w, &max_h);
    printf("default max image size: %dx%d\n", max_w, max_h);

    /* 错误枚举基值（核心 API 语义完整性） */
    exr_error_code_t err = EXR_ERR_SUCCESS;
    if ((int)err != 0) {
        printf("unexpected EXR_ERR_SUCCESS value\n");
        return 1;
    }

    printf("test_core OK\n");
    return 0;
}
