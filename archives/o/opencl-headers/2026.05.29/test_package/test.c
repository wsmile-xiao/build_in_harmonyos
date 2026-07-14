#include <stdio.h>
#include <CL/opencl.h>

int main(void) {
    /* R34 反空壳：验证头文件真实可被预处理且定义了 OpenCL API 符号 */
    cl_platform_id platform = NULL;
    cl_uint major = CL_VERSION_MAJOR(0);
    /* 直接校验 CL_SUCCESS 宏值，而非 err != CL_SUCCESS（后者恒假） */
    if (CL_SUCCESS != 0) {
        fprintf(stderr, "CL_SUCCESS macro value invalid: %d\n", CL_SUCCESS);
        return 1;
    }
    printf("opencl-headers: CL_SUCCESS=%d, CL_VERSION_MAJOR=%u, sizeof(cl_platform_id)=%zu\n",
           CL_SUCCESS, major, sizeof(platform));
    printf("opencl.h standalone test PASSED.\n");
    return 0;
}
