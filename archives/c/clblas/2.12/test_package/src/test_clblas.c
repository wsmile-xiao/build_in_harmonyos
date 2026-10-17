/* clblas test_package 消费者测试：调用 clBLAS C API（clblasSaxpy）
 * 验证 libclBLAS 头文件/链接正确；运行时需真实 OpenCL 设备执行内核，
 * OHOS 预检机无 OpenCL ICD 驱动时如实报告（不伪造通过）。 */
#include <CL/cl.h>
#include <clBLAS.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_PLATFORMS 8

static void release_resources(cl_context ctx, cl_command_queue queue,
                              cl_mem xbuf, cl_mem ybuf) {
    if (ybuf) clReleaseMemObject(ybuf);
    if (xbuf) clReleaseMemObject(xbuf);
    if (queue) clReleaseCommandQueue(queue);
    if (ctx) clReleaseContext(ctx);
}

int main(void) {
    cl_context ctx = NULL;
    cl_command_queue queue = NULL;
    cl_mem xbuf = NULL, ybuf = NULL;

    /* 1) 探测 OpenCL 平台：无平台则如实退出（设备依赖，非库缺陷） */
    cl_uint num_platforms = 0;
    cl_int err = clGetPlatformIDs(0, NULL, &num_platforms);
    if (err != CL_SUCCESS || num_platforms == 0) {
        printf("SKIP: 无可用 OpenCL 平台 (err=%d, platforms=%u)——OHOS 预检机"
               "未安装 OpenCL ICD 驱动，无法执行内核（设备依赖，如实记录）\n",
               (int)err, num_platforms);
        return 2;
    }
    printf("OK: OpenCL 平台可用 (platforms=%u)\n", num_platforms);

    /* 2) 平台就绪时创建 context/queue，调用 clblasSaxpy 验证库 API */
    /* 上界约束：仅查询 min(num_platforms, MAX_PLATFORMS) 个平台，
     * 避免平台数超过数组容量时 clGetPlatformIDs 越界写（AI review P2） */
    cl_uint fetch = num_platforms < MAX_PLATFORMS ? num_platforms : MAX_PLATFORMS;
    cl_platform_id platforms[MAX_PLATFORMS];
    err = clGetPlatformIDs(fetch, platforms, NULL);
    if (err != CL_SUCCESS) {
        printf("FAIL: clGetPlatformIDs 列表失败 err=%d\n", (int)err);
        return 1;
    }
    cl_device_id device;
    err = clGetDeviceIDs(platforms[0], CL_DEVICE_TYPE_ALL, 1, &device, NULL);
    if (err != CL_SUCCESS) {
        printf("SKIP: 平台无设备 (err=%d)——设备依赖，如实记录\n", (int)err);
        return 2;
    }
    ctx = clCreateContext(NULL, 1, &device, NULL, NULL, &err);
    if (err != CL_SUCCESS || !ctx) {
        printf("FAIL: clCreateContext err=%d\n", (int)err);
        return 1;
    }
    queue = clCreateCommandQueue(ctx, device, 0, &err);
    if (err != CL_SUCCESS || !queue) {
        printf("FAIL: clCreateCommandQueue err=%d\n", (int)err);
        release_resources(ctx, NULL, NULL, NULL);
        return 1;
    }

    const size_t N = 8;
    cl_float x[8] = {1, 2, 3, 4, 5, 6, 7, 8};
    cl_float y[8] = {0, 0, 0, 0, 0, 0, 0, 0};
    xbuf = clCreateBuffer(ctx, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR,
                          sizeof(x), x, &err);
    ybuf = clCreateBuffer(ctx, CL_MEM_READ_WRITE, sizeof(y), NULL, &err);
    if (err != CL_SUCCESS || !xbuf || !ybuf) {
        printf("FAIL: clCreateBuffer err=%d\n", (int)err);
        release_resources(ctx, queue, xbuf, ybuf);
        return 1;
    }
    clblasStatus st = clblasSetup();
    if (st != clblasSuccess) {
        printf("FAIL: clblasSetup 返回 %d\n", (int)st);
        release_resources(ctx, queue, xbuf, ybuf);
        return 1;
    }
    /* 初始化事件句柄并检查返回值：调用失败时不等待/释放垃圾句柄
     * （AI review P2：未初始化 ev + 未检查 clblasSaxpy 返回值） */
    cl_event ev = NULL;
    st = clblasSaxpy(N, 2.0f, xbuf, 0, 1, ybuf, 0, 1, 1, &queue, 0, NULL, &ev);
    if (st != clblasSuccess) {
        printf("FAIL: clblasSaxpy 返回 %d\n", (int)st);
        if (ev) clReleaseEvent(ev);
        clblasTeardown();
        release_resources(ctx, queue, xbuf, ybuf);
        return 1;
    }
    err = clWaitForEvents(1, &ev);
    if (err != CL_SUCCESS) {
        printf("FAIL: clWaitForEvents err=%d\n", (int)err);
    }
    clReleaseEvent(ev);
    /* 检查读回返回值（AI review P3）：读回失败时结果判定误导 */
    err = clEnqueueReadBuffer(queue, ybuf, CL_TRUE, 0, sizeof(y), y, 0, NULL, NULL);
    if (err != CL_SUCCESS) {
        printf("FAIL: clEnqueueReadBuffer err=%d\n", (int)err);
        clblasTeardown();
        release_resources(ctx, queue, xbuf, ybuf);
        return 1;
    }
    clblasTeardown();
    release_resources(ctx, queue, xbuf, ybuf);
    printf("OK: clblasSaxpy 完成，y[0]=%g（期望 2.0）\n", y[0]);
    if (y[0] != 2.0f) {
        printf("FAIL: y[0]=%g != 2.0\n", y[0]);
        return 1;
    }
    return 0;
}
