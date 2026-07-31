// vesin 0.6.1 —— 真实近邻表计算验证（非 dlopen/链接空壳）。
//
// 判据取自可手算的几何：四点摆成边长 1.0 的正方形，非周期、半表。
//   · 边（长 1.0）4 条：0-1, 1-2, 2-3, 3-0
//   · 对角线（长 √2≈1.414）2 条：0-2, 1-3
// cutoff=1.5 时两者都在内 → 应恰好 6 对；收到 1.2 → 只剩 4 条边。
// 两个 cutoff 都测，是为了同时验「算得出」与「cutoff 真在起作用」——
// 只测前者的话，一个永远返回全部点对的实现也能蒙混过关。
#include <stdint.h>
#include <stddef.h>
#include <vesin.h>

#include <cstdio>
#include <cstring>

static int failures = 0;
#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (!(cond)) {                                                         \
            std::fprintf(stderr, "[FAIL] %s  (%s:%d)\n", msg, __FILE__,        \
                         __LINE__);                                            \
            ++failures;                                                        \
        } else {                                                               \
            std::printf("[ok] %s\n", msg);                                     \
        }                                                                      \
    } while (0)

static size_t count_pairs(double cutoff, bool *ok) {
    const double points[4][3] = {
        {0.0, 0.0, 0.0}, {1.0, 0.0, 0.0}, {1.0, 1.0, 0.0}, {0.0, 1.0, 0.0},
    };
    const double box[3][3] = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}};
    const bool periodic[3] = {false, false, false};

    VesinOptions options;
    std::memset(&options, 0, sizeof(options));
    options.cutoff = cutoff;
    options.full = false;                 // 半表：只要 i->j
    options.sorted = true;
    options.algorithm = VesinAutoAlgorithm;
    options.return_distances = true;

    VesinDevice device;
    device.type = VesinCPU;
    device.device_id = 0;

    VesinNeighborList neighbors;
    std::memset(&neighbors, 0, sizeof(neighbors));

    const char *err = nullptr;
    int rc = vesin_neighbors(points, 4, box, periodic, device, options,
                             &neighbors, &err);
    if (rc != 0) {
        std::fprintf(stderr, "vesin_neighbors 失败: %s\n", err ? err : "(无消息)");
        *ok = false;
        return 0;
    }

    size_t n = neighbors.length;
    *ok = true;
    // 顺带核对每对的距离都落在 cutoff 内——防止「对数对了但距离算错」蒙混过去
    for (size_t k = 0; k < n; ++k) {
        double d = neighbors.distances[k];
        if (!(d > 0.0 && d <= cutoff + 1e-9)) {
            std::fprintf(stderr, "第 %zu 对距离 %.6f 不在 (0, %.3f]\n", k, d, cutoff);
            *ok = false;
        }
    }
    vesin_free(&neighbors);
    return n;
}

int main() {
    bool ok = false;

    size_t n_wide = count_pairs(1.5, &ok);
    CHECK(ok, "cutoff=1.5 计算成功且所有距离都在 cutoff 内");
    CHECK(n_wide == 6, "cutoff=1.5 → 6 对（4 条边 + 2 条对角线）");
    if (n_wide != 6) std::fprintf(stderr, "       实得 %zu\n", n_wide);

    size_t n_narrow = count_pairs(1.2, &ok);
    CHECK(ok, "cutoff=1.2 计算成功且所有距离都在 cutoff 内");
    CHECK(n_narrow == 4, "cutoff=1.2 → 4 对（对角线 1.414 被排除，证明 cutoff 生效）");
    if (n_narrow != 4) std::fprintf(stderr, "       实得 %zu\n", n_narrow);

    if (failures) {
        std::fprintf(stderr, "\nvesin: %d 项断言失败\n", failures);
        return 1;
    }
    std::printf("\nvesin 0.6.1: 全部断言通过\n");
    return 0;
}
