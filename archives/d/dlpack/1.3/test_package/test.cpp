// test_package/test.cpp — dlpack 消费者测试
// 验证可包含 dlpack.h 并创建/读取 DLTensor 结构。
#include <dlpack/dlpack.h>
#include <cstdio>

int main() {
    // 创建 DLTensor（2x3 float32 矩阵描述）
    float data[6] = {1, 2, 3, 4, 5, 6};
    int64_t shape[2] = {2, 3};
    int64_t strides[2] = {3, 1};

    DLTensor tensor;
    tensor.data = data;
    tensor.device = DLDevice{kDLCPU, 0};
    tensor.ndim = 2;
    tensor.dtype = DLDataType{kDLFloat, 32, 1};
    tensor.shape = shape;
    tensor.strides = strides;
    tensor.byte_offset = 0;

    // 验证结构字段
    if (tensor.ndim != 2 || tensor.dtype.code != kDLFloat || tensor.dtype.bits != 32) {
        fprintf(stderr, "FAIL: DLTensor fields mismatch\n");
        return 1;
    }
    if (tensor.shape[0] != 2 || tensor.shape[1] != 3) {
        fprintf(stderr, "FAIL: shape mismatch\n");
        return 1;
    }
    if (static_cast<float *>(tensor.data)[5] != 6.0f) {
        fprintf(stderr, "FAIL: data access mismatch\n");
        return 1;
    }

    printf("dlpack smoke test: PASS (DLTensor 2x3 ok)\n");
    return 0;
}
