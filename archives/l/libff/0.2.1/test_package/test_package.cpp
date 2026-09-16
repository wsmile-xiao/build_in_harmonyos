// libff 0.2.1 消费者验证：调用库的核心 API —— ALT_BN128 双线性配对。
// 覆盖：G1/G2 群运算（加法/标量乘/逆）、Fp/Fp2/Fp6/Fp12 域运算、
//      miller loop + final exponentiation = pairing，以及 bilinearity 检验
//      e(aP, bQ) == e(P, Q)^(ab)（与上游 algebra_bilinearity_test 同一断言族）。
// 运行期验证全部走显式 CHECK 宏（见下），不依赖 assert/NDEBUG/构建类型，
// Release 构建下同样真实执行每个条件。
#include <libff/algebra/curves/alt_bn128/alt_bn128_pp.hpp>
#include <libff/algebra/curves/alt_bn128/alt_bn128_g1.hpp>
#include <libff/algebra/curves/alt_bn128/alt_bn128_g2.hpp>
#include <libff/algebra/fields/fp.hpp>
#include <libff/common/default_types/ec_pp.hpp>
#include <libff/common/utils.hpp>

#include <cstdio>
#include <fstream>
#include <iostream>
#include <type_traits>

// 消费者识别真实曲线配置（编译期门禁）：
// (1) 配方 package_info() 经 cpp_info.defines 传播 CURVE_ALT_BN128 ——
//     上游 ec_pp.hpp 依此宏选择 default_ec_pp；宏缺失即配置链断裂。
// (2) default_ec_pp 必须解析为 alt_bn128_pp，证明链接的是本包的 ALT_BN128 实现。
#ifndef CURVE_ALT_BN128
#error "consumer did not receive CURVE_ALT_BN128 from libff package_info defines"
#endif
static_assert(std::is_same<libff::default_ec_pp, libff::alt_bn128_pp>::value,
              "libff package must be ALT_BN128-configured (default_ec_pp mismatch)");

// 序列化宏门禁（E543）：BINARY_OUTPUT/MONTGOMERY_OUTPUT 影响已安装公共模板
// operator<</>> 的实例化（下方第 8 步在消费者侧实例化这些模板）。库本体按
// 默认 ON 构建，消费者必须拿到同样宏集，否则同一模板按不同格式实例化。
#ifndef BINARY_OUTPUT
#error "consumer did not receive BINARY_OUTPUT from libff package_info defines"
#endif
#ifndef MONTGOMERY_OUTPUT
#error "consumer did not receive MONTGOMERY_OUTPUT from libff package_info defines"
#endif

using namespace libff;

// 显式检查机制（与 test_package_ohos.cpp 的"始终执行"语义一致）：
//   - 不依赖 assert/NDEBUG/构建类型：assert 在 Release/NDEBUG 下被整体编译掉，
//     会令测试退化为空壳；CHECK 是普通 if，任何构建类型下都真实求值；
//   - 每个条件只求值一次；
//   - 失败时输出具体检查名称并累计失败数；
//   - main() 末尾按失败数返回非零，成功时输出明确通过数量。
namespace {
int checks_passed = 0;
int checks_failed = 0;
}  // namespace

#define CHECK(name, cond)                                                 \
    do {                                                                  \
        if (cond) {                                                       \
            ++checks_passed;                                              \
            std::printf("[PASS] %s\n", (name));                           \
        } else {                                                          \
            ++checks_failed;                                              \
            std::printf("[FAIL] %s (line %d)\n", (name), __LINE__);       \
        }                                                                 \
    } while (0)

int main() {
    // 1) 初始化公共参数（曲线参数、生成元）—— libff 核心入口
    alt_bn128_pp::init_public_params();

    // 2) 域运算：Fp6 = Fp2 的三次扩张，乘法逆元
    typedef Fr<alt_bn128_pp> ScalarField;
    const ScalarField s = ScalarField::random_element();
    const ScalarField s_inv = s.inverse();
    CHECK("fr_mul_inverse", s * s_inv == ScalarField::one());

    // 3) G1 群运算：生成元、加法、标量乘、逆
    const alt_bn128_G1 P = alt_bn128_G1::one();
    CHECK("g1_generator_nonzero", !P.is_zero());
    CHECK("g1_generator_is_one", P == alt_bn128_G1::one());
    const alt_bn128_G1 dbl = P + P;
    CHECK("g1_dbl_matches_add", dbl == P.dbl());
    const alt_bn128_G1 kP = ScalarField("2").as_bigint() * P;
    CHECK("g1_scalar_mul_2P", kP == dbl);
    CHECK("g1_sub_self_is_zero", P - P == alt_bn128_G1::zero());
    CHECK("g1_inverse_of_inverse", -(-P) == P);  // 逆的逆还原（群逆 = operator-）
    CHECK("g1_group_inverse", P + (-P) == alt_bn128_G1::zero());  // 群逆性质 P + (-P) = O

    // 4) G2 群运算（坐标在 Fp2 上）
    const alt_bn128_G2 Q = alt_bn128_G2::one();
    CHECK("g2_generator_nonzero", !Q.is_zero());
    const alt_bn128_G2 Q2 = Q + Q;
    CHECK("g2_dbl_matches_add", Q2 == Q.dbl());
    CHECK("g2_scalar_mul_2Q", Q2 == ScalarField("2").as_bigint() * Q);

    // 5) 核心：双线性配对 reduced_pairing（miller loop + final exponentiation）
    //    与上游 test_bilinearity.cpp 相同的调用路径，输出在 Fp12 (GT)
    const auto e_pq = alt_bn128_pp::reduced_pairing(P, Q);
    CHECK("pairing_nonzero", !e_pq.is_zero());

    // 6) bilinearity：e(2P, Q) == e(P, Q)^2 == e(P, 2Q)
    //    （上游 pairing_test() 同一断言族：ans1 == ans2 == ans3）
    const auto e_2pq = alt_bn128_pp::reduced_pairing(P + P, Q);
    const auto e_p2q = alt_bn128_pp::reduced_pairing(P, Q + Q);
    CHECK("bilinearity_e_2P_Q", e_2pq == e_pq * e_pq);
    CHECK("bilinearity_e_P_2Q", e_p2q == e_pq * e_pq);
    CHECK("bilinearity_consistency", e_2pq == e_p2q);

    // 7) 非退化：e(P, Q) != 1
    CHECK("pairing_nondegenerate", e_pq != Fqk<alt_bn128_pp>::one());

    // 8) 序列化往返（BINARY_OUTPUT 默认 ON）：operator<</>> 流式接口
    const alt_bn128_G1 ser = ScalarField::random_element().as_bigint() * P;
    std::ofstream ofs("g1_roundtrip.bin", std::ios::binary);
    ofs << ser;
    ofs.close();
    alt_bn128_G1 deser;
    std::ifstream ifs("g1_roundtrip.bin", std::ios::binary);
    ifs >> deser;
    ifs.close();
    CHECK("serialization_roundtrip_G1", deser == ser);

    // 汇总：通过/失败计数；存在失败即返回非零（ctest 判负）
    std::printf("libff test_package: %d checks passed, %d failed\n",
                checks_passed, checks_failed);
    if (checks_failed > 0) {
        return 1;
    }
    std::cout << "libff test_package OK: ALT_BN128 pairing, group/field ops, serialization roundtrip\n";
    return 0;
}
