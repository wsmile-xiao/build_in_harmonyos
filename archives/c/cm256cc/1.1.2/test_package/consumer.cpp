#include <cm256cc/cm256.h>

#include <cstdio>
#include <cstring>
#include <cstdlib>

// Consumer test: exercise the real CM256 encode/decode API.
// 10 original blocks + 4 recovery blocks; lose the first 2 originals and
// recover them through cm256_decode, then compare with the original data.
int main() {
    CM256 cm256;
    if (!cm256.isInitialized()) {
        std::fprintf(stderr, "FAIL: CM256 initialization\n");
        return 1;
    }

    CM256::cm256_encoder_params params;
    params.BlockBytes = 64;
    params.OriginalCount = 10;
    params.RecoveryCount = 4;

    static const int OriginalBytes = params.OriginalCount * params.BlockBytes;
    unsigned char* original = new unsigned char[OriginalBytes];
    for (int i = 0; i < OriginalBytes; ++i) {
        original[i] = (unsigned char)(i * 7 + 3);
    }

    CM256::cm256_block blocks[256];
    for (int i = 0; i < params.OriginalCount; ++i) {
        blocks[i].Block = original + i * params.BlockBytes;
        blocks[i].Index = CM256::cm256_get_original_block_index(params, i);
    }

    unsigned char* recovery = new unsigned char[params.RecoveryCount * params.BlockBytes];
    if (cm256.cm256_encode(params, blocks, recovery)) {
        std::fprintf(stderr, "FAIL: cm256_encode returned an error\n");
        return 1;
    }
    std::printf("PASS: cm256_encode produced %d recovery blocks\n", params.RecoveryCount);

    unsigned char* backup = new unsigned char[OriginalBytes];
    std::memcpy(backup, original, OriginalBytes);

    // Simulate loss of the first two originals; substitute recovery blocks.
    const int lost = 2;
    for (int i = 0; i < lost; ++i) {
        blocks[i].Block = recovery + i * params.BlockBytes;
        blocks[i].Index = CM256::cm256_get_recovery_block_index(params, i);
    }

    if (cm256.cm256_decode(params, blocks)) {
        std::fprintf(stderr, "FAIL: cm256_decode returned an error\n");
        return 1;
    }
    std::printf("PASS: cm256_decode recovered %d lost blocks\n", lost);

    for (int i = 0; i < lost; ++i) {
        if (std::memcmp(blocks[i].Block, backup + i * params.BlockBytes,
                        params.BlockBytes) != 0) {
            std::fprintf(stderr, "FAIL: recovered block %d does not match original\n", i);
            return 1;
        }
    }
    std::printf("PASS: recovered blocks match the original data\n");

    delete[] original;
    delete[] recovery;
    delete[] backup;
    std::printf("ALL PASS: cm256cc consumer test (3 assertions)\n");
    return 0;
}
