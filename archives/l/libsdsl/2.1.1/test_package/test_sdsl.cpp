#include <cstdint>
#include <cstdio>

#include <sdsl/bit_vectors.hpp>
#include <sdsl/int_vector.hpp>
#include <sdsl/rank_support_v.hpp>
#include <sdsl/select_support_mcl.hpp>
#include <sdsl/sd_vector.hpp>

#define CHECK(n, cond) do { \
    if (!(cond)) { printf("CHECK %d: FAIL (%s:%d)\n", n, __FILE__, __LINE__); return 1; } \
    printf("CHECK %d: OK\n", n); \
} while (0)

int main()
{
    // 1: bit_vector size and stored bits (in-memory only, no /tmp I/O).
    sdsl::bit_vector b(64, 0);
    b[3] = 1; b[10] = 1; b[63] = 1;
    CHECK(1, b.size() == 64 && b[3] == 1 && b[10] == 1 && b[63] == 1 && b[0] == 0);

    // 2: rank_support_v over the bit_vector.
    sdsl::rank_support_v<> rs(&b);
    CHECK(2, rs.rank(64) == 3);
    CHECK(3, rs.rank(11) == 2);

    // 4: select_support_mcl over the bit_vector.
    sdsl::select_support_mcl<> ss(&b);
    CHECK(4, ss.select(1) == 3 && ss.select(2) == 10 && ss.select(3) == 63);

    // 5: int_vector roundtrip with explicit width.
    sdsl::int_vector<> iv(8, 0, 8);
    for (uint64_t i = 0; i < iv.size(); ++i) iv[i] = i * 3;
    bool iv_ok = true;
    for (uint64_t i = 0; i < iv.size(); ++i) { if (iv[i] != i * 3) { iv_ok = false; break; } }
    CHECK(5, iv_ok && iv.width() == 8);

    // 6: sd_vector compressed view preserves size and popcount.
    sdsl::sd_vector<> sdb(b);
    sdsl::sd_vector<>::rank_1_type rsdb(&sdb);
    CHECK(6, sdb.size() == 64 && rsdb.rank(64) == 3);

    printf("test_sdsl: all 6 checks passed\n");
    return 0;
}
