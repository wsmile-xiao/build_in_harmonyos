// HarmonyOS 专项消费者测试: libff 0.2.1 on OHOS armv8 (clang 15 / libc++)
//
// 该测试不是上游测试的复述, 而是针对本次适配中实际产生差异的平台点做真实验证:
//   1. NO_PROCPS 回退路径: OHOS 无 libprocps, 配方以 WITH_PROCPS=OFF 构建包,
//      profiling.hpp 公共 API (start_profiling/print_mem/enter_block/leave_block)
//      必须仍可用且不引用 procps 符号 (E077 邻域: 包内已核实 0 个 proc 引用)。
//   2. aarch64 可移植 Montgomery 路径: USE_ASM 汇编仅在 __x86_64__ 激活
//      (fp.tcc:26), OHOS armv8 走 GMP mpn + C++ 路径。验证 Fp_model::invert /
//      sqrt(Tonelli-Shanks) / squared 与 bigint<->mpz 互操作在 aarch64 上的
//      数值正确性 (环公理 + 已知平方根往返)。
//   3. 域/群阶常数位级一致性: alt_bn128 的 q/r 模数必须与上游 x86-64 参考
//      逐位一致 (bn128_init.cpp:38,63 与 alt_bn128_init.cpp:41,61 同源),
//      证明跨架构配置链未断裂。
//   4. 配对确定性: 同输入的 reduced_pairing 两次计算结果逐位相等
//      (miller loop + final exp 在 aarch64 上无未初始化/UB 漂移)。
//   5. 特殊点序列化: zero 元素经 operator<</>> 往返 (is_zero 标志路径)。
//   6. 包内 libff.a 对象级检查: 解析消费者实际链接的 conan 包归档
//      (ar GNU 长名表 + ELF 头), 全部 .obj 成员必须为 ELF64/小端/ET_REL/
//      本机 e_machine (aarch64: EM_AArch64=183), ALT_BN128 5 对象 + 公共
//      3 TU 齐备, 总数 24, 且无 bn128_* (x86-64 only) 对象混入。
#include <libff/algebra/curves/alt_bn128/alt_bn128_pp.hpp>
#include <libff/algebra/curves/alt_bn128/alt_bn128_g1.hpp>
#include <libff/algebra/curves/alt_bn128/alt_bn128_g2.hpp>
#include <libff/algebra/fields/bigint.hpp>
#include <libff/algebra/fields/fp.hpp>
#include <libff/common/default_types/ec_pp.hpp>
#include <libff/common/profiling.hpp>
#include <libff/common/utils.hpp>

#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>
#include <type_traits>
#include <vector>

// 消费者识别真实曲线配置 (与 test_package.cpp 同一编译期门禁)
#ifndef CURVE_ALT_BN128
#error "consumer did not receive CURVE_ALT_BN128 from libff package_info defines"
#endif
static_assert(std::is_same<libff::default_ec_pp, libff::alt_bn128_pp>::value,
              "libff package must be ALT_BN128-configured (default_ec_pp mismatch)");

// 对象级检查（check 6）依赖配方注入的包内归档绝对路径
// （CMakeDeps 的 libff::ff 是 INTERFACE 包装，无 $<TARGET_FILE>）
#ifndef LIBFF_ARCHIVE_PATH
#error "LIBFF_ARCHIVE_PATH must be injected via CMake by the test_package conanfile"
#endif

using namespace libff;

namespace {

// ── 1. NO_PROCPS 回退路径 ──────────────────────────────────────────
// 包以 WITH_PROCPS=OFF 构建 (OHOS 无 libprocps)。profiling 公共 API 必须可用:
// enter_block/leave_block 走纯计时+计数路径, print_mem 走 NO_PROCPS 提示分支。
// 运行级证据: 若包误链 procps, 这些调用会因 look_up_our_self 未定义而直接
// 链接失败 (静态包在 test_package 链接期即暴露); 运行通过即回退路径成立。
bool check_noprocps_profiling_runtime() {
    start_profiling();
    enter_block("ohos profiling probe");
    const long long t0 = get_nsec_time();
    volatile long long acc = 0;
    for (int i = 0; i < 100000; ++i) acc += i;
    const long long t1 = get_nsec_time();
    (void)acc;
    leave_block("ohos profiling probe");
    // 计时器单调且非零 (clock_gettime(CLOCK_PROCESS_CPUTIME_ID) 在 OHOS 上可用)
    if (t1 < t0) return false;
    // print_mem 在 NO_PROCPS 下只打印提示, 不崩溃 (输出进 stdout)
    print_mem("ohos probe");
    return true;
}

// ── 2a. aarch64 Montgomery 域运算: invert / sqrt 往返 ─────────────
// USE_ASM 仅 x86-64; 此处全部走 GMP mpn C++ 路径。
// 对任意非零 x: sqrt(x^2) == x (Tonelli-Shanks 正确性),
// 且 x * x.inverse() == 1 (扩展欧几里得/费马小定理路径)。
bool check_fp_arithmetic_portable_path() {
    typedef alt_bn128_Fr ScalarField;
    for (int i = 0; i < 32; ++i) {
        const ScalarField x = ScalarField::random_element();
        if (x.is_zero()) continue;
        if (x * x.inverse() != ScalarField::one()) return false;
        if (x.inverse().inverse() != x) return false;
        const ScalarField sq = x.squared();
        if (sq != x * x) return false;
        const ScalarField rt = sq.sqrt();  // 平方元素的平方根必须还原
        if (rt != x && rt != -x) return false;
    }
    return true;
}

// ── 2b. bigint <-> mpz 互操作 (GMP 硬依赖的传递路径) ────────────────
// libff 公开头 bigint.hpp 暴露 mpz 构造/导出; OHOS 上链接的是 conan gmp/6.3.0.1。
bool check_bigint_mpz_interop() {
    typedef alt_bn128_Fr Fr;               // Fp_model<4, alt_bn128_modulus_r>
    typedef bigint<Fr::num_limbs> big;     // 4-limb (254-bit 域)
    const big src("21888242871839275222246405745257275088548364400416034343698204186575808495617");
    mpz_t m;
    mpz_init(m);
    src.to_mpz(m);                 // bigint -> mpz
    const big round(m);            // mpz -> bigint
    mpz_clear(m);
    if (round != src) return false;
    // 高位 limb 非零: mpn 路径要求最高 limb 非零 (modulus_is_valid 语义)
    if (src.data[big::N - 1] == 0) return false;
    return true;
}

// ── 3. 域/群阶常数跨架构位级一致性 ─────────────────────────────────
// 参考值 = 上游 bn128_init.cpp / alt_bn128_init.cpp 中的十进制常数 (x86-64 与
// aarch64 同一份源码)。任何 Montgomery 常数/模数初始化漂移都会在此暴露。
// 注意：刻意不经过 operator<< —— 包定义 BINARY_OUTPUT 后 bigint/Fp 的流序列
// 化按二进制 limbs 输出 (bigint.tcc:189 二进制分支)，十进制比对必然失败；
// 这正是"后端替换非等价、序列化不能默认互操作"的活证据。因此这里直接经
// to_mpz() 做十进制比对，与序列化宏解耦。
bool check_curve_constants_bit_exact() {
    const char *q_ref =
        "21888242871839275222246405745257275088696311157297823662689037894645226208583";
    const char *r_ref =
        "21888242871839275222246405745257275088548364400416034343698204186575808495617";
    typedef alt_bn128_Fq BaseField;        // Fp_model<4, alt_bn128_modulus_q>
    typedef alt_bn128_Fr ScalarField;      // Fp_model<4, alt_bn128_modulus_r>
    std::ostringstream qs, rs;
    {
        mpz_t q, r;
        mpz_init(q); mpz_init(r);
        BaseField::mod.to_mpz(q);          // 十进制无关 BINARY_OUTPUT/MONTGOMERY_OUTPUT
        ScalarField::mod.to_mpz(r);
        qs << q;  // mpz_out_str 十进制
        rs << r;
        mpz_clear(q); mpz_clear(r);
    }
    return qs.str() == q_ref && rs.str() == r_ref;
}

// ── 4. 配对确定性 (同输入两次计算逐位相等) ─────────────────────────
// miller loop + final exponentiation 涉及数千次域乘; aarch64 上任何未初始化
// 或符号漂移都会让两次结果出现差异。
bool check_pairing_determinism() {
    const alt_bn128_G1 P = alt_bn128_G1::one();
    const alt_bn128_G2 Q = alt_bn128_G2::one();
    const auto e1 = alt_bn128_pp::reduced_pairing(P, Q);
    const auto e2 = alt_bn128_pp::reduced_pairing(P, Q);
    if (!(e1 == e2)) return false;
    std::ostringstream s1, s2;
    s1 << e1;
    s2 << e2;
    return s1.str() == s2.str();
}

// ── 5. 特殊点 (zero) 序列化往返 ────────────────────────────────────
// 上游 operator<< 对 G1/G2 写 is_zero 标志位; 随机点往返已在 test_package 覆盖,
// 此处覆盖 zero 特殊分支 (OHOS 上流路径与字节序无关, 但 zero 分支独享代码路径)。
template <typename G>
bool check_zero_serialization() {
    const G z = G::zero();
    std::ostringstream oss;
    oss << z;
    std::istringstream iss(oss.str());
    G back;
    iss >> back;
    return back == z && back.is_zero();
}

// ── 6. 包内 libff.a 对象级检查（ar + ELF 头解析）────────────────────
// 消费者在 OHOS 上实际链接的静态归档位于 conan 包目录（CMake 以
// $<TARGET_FILE:libff::ff> 编译期注入绝对路径）。逐成员解析 ar（GNU
// 符号表/长名表）与 ELF 头，验证包内对象构成：
//   - 全部 .obj 成员均为 ELF64 / 小端 / ET_REL / 本机 e_machine
//     （aarch64: EM_AArch64=183；任何交叉污染在此直接暴露）;
//   - ALT_BN128 曲线 5 对象（g1/g2/init/pairing/pp）齐备 —— 包内真实
//     曲线实现的对象级证据，与编译期 static_assert 门禁互补;
//   - 公共 TU（double/profiling/utils）齐备;
//   - 无 bn128_*（无 alt_ 前缀，x86-64-only ate-pairing 路径）对象混入;
//   - 总数 24 = 上游 CURVE!=BN128 分支的固定 TU 集（alt_bn128/edwards/
//     mnt4/mnt6 各 5 + mnt46_common + 3 公共，libff/CMakeLists.txt:27-50）。
#if defined(__aarch64__)
static const unsigned kElfMachineExpected = 183;  // EM_AArch64
#elif defined(__x86_64__) || defined(_M_X64)
static const unsigned kElfMachineExpected = 62;   // EM_X86_64
#else
#error "test_package_ohos: unsupported host arch for archive object check"
#endif

bool check_package_archive_objects() {
    std::FILE *f = std::fopen(LIBFF_ARCHIVE_PATH, "rb");
    if (!f) return false;
    std::vector<unsigned char> buf;
    unsigned char chunk[65536];
    size_t n;
    while ((n = std::fread(chunk, 1, sizeof chunk, f)) > 0)
        buf.insert(buf.end(), chunk, chunk + n);
    std::fclose(f);
    const size_t sz = buf.size();
    if (sz < 8 || std::memcmp(buf.data(), "!<arch>\n", 8) != 0) return false;

    size_t off = 8;
    std::string longtab;
    int members = 0, machine_ok = 0, alt_objs = 0;
    bool has_double = false, has_profiling = false, has_utils = false;
    bool has_bn128 = false;
    while (off + 60 <= sz) {
        const unsigned char *h = buf.data() + off;
        size_t msize = 0;
        for (int i = 48; i < 58; ++i)
            if (h[i] >= '0' && h[i] <= '9') msize = msize * 10 + (h[i] - '0');
        if (off + 60 + msize > sz) return false;  // 截断/损坏的归档
        const unsigned char *data = h + 60;

        char namebuf[17];
        std::memcpy(namebuf, h, 16);
        namebuf[16] = '\0';
        std::string name(namebuf);

        if (name.compare(0, 2, "//") == 0) {
            // GNU 长名表
            longtab.assign(reinterpret_cast<const char *>(data), msize);
        } else {
            if (name[0] == '/' && !longtab.empty()) {
                // "/<offset>" 长名引用；"/"+全空格（符号表）无数字，跳过
                size_t lo = 0;
                bool digits = false;
                for (size_t i = 1; i < 16 && name[i] >= '0' && name[i] <= '9'; ++i) {
                    lo = lo * 10 + (name[i] - '0');
                    digits = true;
                }
                if (digits) {
                    if (lo >= longtab.size()) return false;
                    const size_t end = longtab.find('\n', lo);
                    if (end == std::string::npos) return false;
                    name = longtab.substr(lo, end - lo);
                    if (!name.empty() && name[name.size() - 1] == '/')
                        name.erase(name.size() - 1);
                } else {
                    name.clear();  // 符号表成员
                }
            } else {
                // 短名（含长名表之前出现的符号表 "/"）：去尾部空格与 '/'
                const size_t cut = name.find_last_not_of(" /");
                if (cut == std::string::npos) name.clear();
                else name.erase(cut + 1);
            }
            const bool is_obj =
                (name.size() >= 4 && name.compare(name.size() - 4, 4, ".obj") == 0) ||
                (name.size() >= 2 && name.compare(name.size() - 2, 2, ".o") == 0);
            if (is_obj) {
                if (msize < 20 || std::memcmp(data, "\x7f" "ELF", 4) != 0) return false;
                ++members;
                const unsigned ei_class = data[4];  // 2 = ELF64
                const unsigned ei_data = data[5];   // 1 = 小端
                const unsigned e_type = data[16] | (data[17] << 8);  // 1 = ET_REL
                const unsigned e_machine = data[18] | (data[19] << 8);
                if (ei_class == 2 && ei_data == 1 && e_type == 1 &&
                    e_machine == kElfMachineExpected)
                    ++machine_ok;
                if (name.compare(0, 10, "alt_bn128_") == 0) ++alt_objs;
                if (name.compare(0, 6, "bn128_") == 0) has_bn128 = true;
                if (name.compare(0, 10, "double.cpp") == 0) has_double = true;
                if (name.compare(0, 13, "profiling.cpp") == 0) has_profiling = true;
                if (name.compare(0, 9, "utils.cpp") == 0) has_utils = true;
            }
        }
        off += 60 + msize + (msize & 1);  // ar 成员 2 字节对齐
    }

    const int common_objs =
        (has_double ? 1 : 0) + (has_profiling ? 1 : 0) + (has_utils ? 1 : 0);
    return members == 24 && machine_ok == members && alt_objs == 5 &&
           common_objs == 3 && !has_bn128;
}

}  // namespace

int main() {
    alt_bn128_pp::init_public_params();
#ifdef MULTICORE
    std::printf("target: OHOS armv8, MULTICORE=on\n");
#else
    std::printf("target: OHOS armv8, MULTICORE=off\n");
#endif

    const bool checks[] = {
        check_noprocps_profiling_runtime(),
        check_fp_arithmetic_portable_path(),
        check_bigint_mpz_interop(),
        check_curve_constants_bit_exact(),
        check_pairing_determinism(),
        check_zero_serialization<alt_bn128_G1>(),
        check_zero_serialization<alt_bn128_G2>(),
        check_package_archive_objects(),
    };
    const char *names[] = {
        "noprocps_profiling_runtime",
        "fp_arithmetic_portable_path",
        "bigint_mpz_interop",
        "curve_constants_bit_exact",
        "pairing_determinism",
        "zero_serialization_G1",
        "zero_serialization_G2",
        "package_archive_objects",
    };
    int failed = 0;
    for (size_t i = 0; i < sizeof(checks) / sizeof(checks[0]); ++i) {
        std::printf("[%s] %s\n", checks[i] ? "PASS" : "FAIL", names[i]);
        if (!checks[i]) ++failed;
    }
    std::printf("%zu checks, %d failed\n", sizeof(checks) / sizeof(checks[0]), failed);
    return failed == 0 ? 0 : 1;
}
