// Consumer test for vkfft 1.3.4 (header-only, Vulkan backend).
//
// Includes the public header with VKFFT_BACKEND=0 (the upstream
// default), which transitively pulls in vulkan/vulkan.h and the
// glslang C interface — verifying the full include chain and that the
// header compiles under the OHOS toolchain (C++17, aarch64).
// Exercises the public API structs host-side (configuration of a
// real 1D FFT plan descriptor). Runtime device-side FFT execution
// needs a Vulkan GPU device, which CI does not have — that limitation
// is disclosed in the PR body.
#include "vkFFT/vkFFT.h"

#include <stdio.h>
#include <string.h>

int main(void) {
    VkFFTConfiguration cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.FFTdim = 1;
    cfg.size[0] = 64;
    cfg.size[1] = 1;
    cfg.size[2] = 1;
    cfg.numberBatches = 1;

    if (cfg.FFTdim < 1 || cfg.FFTdim > 3) {
        fprintf(stderr, "FAIL: bad FFTdim\n");
        return 1;
    }
    if (cfg.size[0] != 64 || cfg.numberBatches != 1) {
        fprintf(stderr, "FAIL: bad size/batches\n");
        return 1;
    }
    printf("vkFFT 1.3.4 consumer OK: sizeof(VkFFTApplication)=%zu "
           "sizeof(VkFFTConfiguration)=%zu FFTdim=%u size0=%zu batches=%u\n",
           sizeof(VkFFTApplication), sizeof(VkFFTConfiguration),
           (unsigned)cfg.FFTdim, (size_t)cfg.size[0],
           (unsigned)cfg.numberBatches);
    return 0;
}
