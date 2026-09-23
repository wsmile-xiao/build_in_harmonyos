#include <cstdio>
#include <torch/torch.h>

int main() {
    // 实质调用被测包（libtorch C++ API，R34）：创建张量并做加法，验证库可加载、计算正确。
    torch::Tensor a = torch::tensor({1.0, 2.0, 3.0});
    torch::Tensor b = torch::tensor({4.0, 5.0, 6.0});
    torch::Tensor c = a + b;
    auto sum = c.sum().item<double>();
    if (std::abs(sum - 21.0) > 1e-6) {
        std::fprintf(stderr, "pytorch test FAILED: unexpected sum %f\n", sum);
        return 1;
    }
    std::printf("test pytorch 2.13.0: OK (1+2+3 + 4+5+6 = %f)\n", sum);
    return 0;
}
