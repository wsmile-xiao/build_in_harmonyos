// lapackpp 2024.10.26 消费者验证（鸿蒙侧 test_package）
// 用上游公开 C++ API（<lapack.hh>）编译并运行消费者程序：
//   - find_package(lapackpp CONFIG REQUIRED) 验证包配置可发现
//   - 断言 LAPACKPP_VERSION / lapack::lapackpp_version() == 20241026
//   - 数值断言：potrf / gesv / getrf / trtri / geqrf / syev / gesvd
//     对照手算参考值或可验证的不变量（如 L·Lᵀ == A、‖Av−λv‖≈0）
//   - 完整消费者用例（第 9 节）：端到端数值管线，模拟真实消费者对
//     SLATE 家族栈（lapackpp + blaspp）的组合使用——建模 → potrf →
//     posv → porfs → pocon → syev/gesvd 独立例程交叉验证，验算一律走
//     blaspp 的 BLAS 调用（gemm/gemv/nrm2），非手写循环
#include <lapack.hh>
#include <blas.hh>

#include <algorithm>
#include <cmath>
#include <complex>
#include <cstdint>
#include <cstdio>
#include <vector>

static int g_fail = 0;
static int g_checks = 0;

#define CHECK_MSG(cond, msg)                                    \
    do {                                                        \
        ++g_checks;                                             \
        if (cond) {                                             \
            std::printf("ok   %s\n", msg);                      \
        } else {                                                \
            std::printf("FAIL %s\n", msg);                      \
            ++g_fail;                                           \
        }                                                       \
    } while (0)

// 矩阵-向量乘（列主序）：y = A*x
static std::vector<double> matvec( const std::vector<double>& A,
                                   const std::vector<double>& x,
                                   int n )
{
    std::vector<double> y( n, 0.0 );
    for (int j = 0; j < n; ++j)
        for (int i = 0; i < n; ++i)
            y[ i ] += A[ i + j*n ] * x[ j ];
    return y;
}

int main()
{
    // ── 1. 版本断言：宏与运行时函数一致，均为 2024.10.26 ──
    CHECK_MSG( LAPACKPP_VERSION == 20241026, "LAPACKPP_VERSION == 20241026" );
    CHECK_MSG( lapack::lapackpp_version() == 20241026,
               "lapackpp_version() == 20241026" );

    // ── 2. potrf：Cholesky 分解 A = L·Lᵀ（A 对称正定，对角占优构造）──
    //    A = [[4,1,0],[1,5,2],[0,2,6]]  →  分解后回乘应还原 A
    {
        const int n = 3;
        //           col-major:  A[0]=4  A[1]=1  A[2]=0
        //                      A[3]=1  A[4]=5  A[5]=2
        //                      A[6]=0  A[7]=2  A[8]=6
        std::vector<double> A = { 4.0, 1.0, 0.0,
                                  1.0, 5.0, 2.0,
                                  0.0, 2.0, 6.0 };
        const std::vector<double> A0 = A;
        int64_t info = lapack::potrf( lapack::Uplo::Lower, n, A.data(), n );
        CHECK_MSG( info == 0, "potrf: info == 0" );
        // LAPACK 只写 uplo 指定的三角形，另一半保留原值；回乘前先清零严格上三角，
        // 否则 L·Lᵀ 会混入残留的原始上三角元素
        for (int j = 0; j < n; ++j)
            for (int i = 0; i < j; ++i)
                A[ i + j*n ] = 0.0;
        // L 是下三角，回乘 L·Lᵀ 应等于原 A
        std::vector<double> LLt( n*n, 0.0 );
        for (int j = 0; j < n; ++j) {
            for (int i = 0; i < n; ++i) {
                double s = 0.0;
                for (int k = 0; k < n; ++k)
                    s += A[ i + k*n ] * A[ j + k*n ];  // A=0 的上三角
                LLt[ i + j*n ] = s;
            }
        }
        bool ok = true;
        for (int i = 0; i < n*n; ++i)
            if (std::abs( LLt[ i ] - A0[ i ] ) > 1e-12)
                ok = false;
        CHECK_MSG( ok, "potrf: L·Lᵀ == A (3x3 SPD)" );
    }

    // ── 3. gesv：求解 A·x = b（列主序，b 覆盖在 B 上）──
    //    A = [[2,1],[1,3]], b = [3,5]  →  解 2x+y=3, x+3y=5 → x=[0.8,1.4]
    {
        const int n = 2;
        std::vector<double> A = { 2.0, 1.0,
                                  1.0, 3.0 };
        std::vector<double> B = { 3.0, 5.0 };
        std::vector<int64_t> ipiv( n );
        int64_t info = lapack::gesv( n, 1, A.data(), n, ipiv.data(),
                                     B.data(), n );
        CHECK_MSG( info == 0, "gesv: info == 0" );
        bool ok = std::abs( B[ 0 ] - 0.8 ) < 1e-12
               && std::abs( B[ 1 ] - 1.4 ) < 1e-12;
        CHECK_MSG( ok, "gesv: x == [0.8, 1.4]" );
    }

    // ── 4. getrf：LU 分解 A = P·L·U，再 getrs 求解，残差应≈0 ──
    {
        const int n = 3;
        std::vector<double> A = { 0.0, 2.0, 1.0,
                                  1.0, 0.0, 3.0,
                                  4.0, 1.0, 0.0 };
        const std::vector<double> A0 = A;
        std::vector<int64_t> ipiv( n );
        int64_t info = lapack::getrf( n, n, A.data(), n, ipiv.data() );
        CHECK_MSG( info == 0, "getrf: info == 0" );
        // 用同一分解求解 A·x = b（b = [1,2,3]），再回代验证残差
        std::vector<double> B = { 1.0, 2.0, 3.0 };
        info = lapack::getrs( lapack::Op::NoTrans, n, 1, A.data(), n,
                              ipiv.data(), B.data(), n );
        CHECK_MSG( info == 0, "getrs: info == 0" );
        std::vector<double> Ax = matvec( A0, B, n );
        bool ok = true;
        for (int i = 0; i < n; ++i)
            if (std::abs( Ax[ i ] - ( i + 1 ) ) > 1e-10)
                ok = false;
        CHECK_MSG( ok, "getrf+getrs: A·x == [1,2,3] (残差 < 1e-10)" );
    }

    // ── 5. trtri：下三角阵取逆后，原阵 · 逆阵 应为单位阵 ──
    {
        const int n = 2;
        // 列主序 {2,1,0,3} → M = [[2,0],[1,3]]（下三角），与 Uplo::Lower 一致
        std::vector<double> U = { 2.0, 1.0,
                                  0.0, 3.0 };
        const std::vector<double> M0 = U;
        int64_t info = lapack::trtri( lapack::Uplo::Lower,
                                      lapack::Diag::NonUnit, n, U.data(), n );
        CHECK_MSG( info == 0, "trtri: info == 0" );
        // 同样清零严格上三角（LAPACK 不触碰另一半）
        for (int j = 0; j < n; ++j)
            for (int i = 0; i < j; ++i)
                U[ i + j*n ] = 0.0;
        // U 现为 M⁻¹，用原阵 M0 左乘：M·M⁻¹ == I
        std::vector<double> I( n*n, 0.0 );
        for (int j = 0; j < n; ++j)
            for (int i = 0; i < n; ++i) {
                double s = 0.0;
                for (int k = 0; k < n; ++k)
                    s += M0[ i + k*n ] * U[ k + j*n ];
                I[ i + j*n ] = s;
            }
        bool ok = true;
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                if (std::abs( I[ i + j*n ] - (i == j ? 1.0 : 0.0) ) > 1e-12)
                    ok = false;
        CHECK_MSG( ok, "trtri: M·M⁻¹ == I (2x2)" );
    }

    // ── 6. geqrf：QR 分解后用 orgqr 还原 Q，Q 应为正交阵（QᵀQ == I）──
    {
        const int m = 4, n = 2;
        std::vector<double> A( m*n );
        for (int j = 0; j < n; ++j)
            for (int i = 0; i < m; ++i)
                A[ i + j*m ] = 1.0 / ( 1.0 + i + j );
        std::vector<double> tau( n );
        int64_t info = lapack::geqrf( m, n, A.data(), m, tau.data() );
        CHECK_MSG( info == 0, "geqrf: info == 0" );
        info = lapack::orgqr( m, n, n, A.data(), m, tau.data() );
        CHECK_MSG( info == 0, "orgqr: info == 0" );
        // A 现在持有 Q（m×n 列正交），检查 QᵀQ == I_n
        std::vector<double> QtQ( n*n, 0.0 );
        for (int j = 0; j < n; ++j)
            for (int i = 0; i < n; ++i) {
                double s = 0.0;
                for (int k = 0; k < m; ++k)
                    s += A[ k + i*m ] * A[ k + j*m ];
                QtQ[ i + j*n ] = s;
            }
        bool ok = true;
        for (int i = 0; i < n; ++i)
            for (int j = 0; j < n; ++j)
                if (std::abs( QtQ[ i + j*n ] - (i == j ? 1.0 : 0.0) ) > 1e-12)
                    ok = false;
        CHECK_MSG( ok, "geqrf+orgqr: QᵀQ == I (4x2)" );
    }

    // ── 7. syev：实对称特征值。2x2 [[2,1],[1,2]] → 特征值 1 与 3 ──
    //    LAPACK dsyev 文档规定特征值按**升序**返回（W[0] ≤ W[1]）
    {
        const int n = 2;
        std::vector<double> A = { 2.0, 1.0,
                                  1.0, 2.0 };
        std::vector<double> S( n );
        int64_t info = lapack::syev( lapack::Job::NoVec, lapack::Uplo::Lower,
                                     n, A.data(), n, S.data() );
        CHECK_MSG( info == 0, "syev: info == 0" );
        bool ok = std::abs( S[ 0 ] - 1.0 ) < 1e-12
               && std::abs( S[ 1 ] - 3.0 ) < 1e-12;
        CHECK_MSG( ok, "syev: eigenvalues == {1, 3} (LAPACK dsyev 升序)" );
    }

    // ── 8. gesvd：奇异值分解 A = [[3,0],[0,2]] → 奇异值 3 与 2 ──
    {
        const int m = 2, n = 2;
        std::vector<double> A = { 3.0, 0.0,
                                  0.0, 2.0 };
        std::vector<double> S( 2 );
        int64_t info = lapack::gesvd( lapack::Job::NoVec, lapack::Job::NoVec,
                                      m, n, A.data(), m, S.data(),
                                      nullptr, 1, nullptr, 1 );
        CHECK_MSG( info == 0, "gesvd: info == 0" );
        bool ok = std::abs( S[ 0 ] - 3.0 ) < 1e-12
               && std::abs( S[ 1 ] - 2.0 ) < 1e-12;
        CHECK_MSG( ok, "gesvd: singular values == {3, 2}" );
    }

    // ── 9. 完整消费者用例：端到端数值管线（n=60 确定性 SPD）──
    //    模拟真实消费者对 SLATE 家族栈（lapackpp + blaspp）的组合使用：
    //    建模 → potrf 分解 → posv 求解 → porfs 迭代精化 → pocon 条件数
    //    估计 → syev/gesvd 独立例程交叉验证。验算一律走 blaspp 的 BLAS
    //    调用（gemm/gemv/nrm2），与真实消费者（如 SLATE）的调用形态一致，
    //    而非手写循环。随机源为可复现 64-bit LCG。
    {
        const int n = 60;
        // 确定性随机源（64-bit LCG）；对角占优保证 SPD
        // （Gershgorin：对角 ≥ 60 > 非对角行和 < 59×0.5 = 29.5）
        uint64_t seed = 0x9E3779B97F4A7C15ULL;
        auto frand = [&seed]() {
            seed = seed * 6364136223846793005ULL + 1442695040888963407ULL;
            return double( (seed >> 33) & 0x7fffffff ) / double( 0x7fffffff );
        };
        std::vector<double> A( n*n, 0.0 );
        for (int j = 0; j < n; ++j)
            for (int i = j; i < n; ++i) {
                double v = (i == j) ? 60.0 + frand()*7.0 : frand()*0.5;
                A[ i + j*n ] = v;
                A[ j + i*n ] = v;  // 对称
            }
        const std::vector<double> A0 = A;

        // 9.1 potrf：Cholesky 分解；L·Lᵀ 由 blas::gemm 验算应还原 A
        std::vector<double> L = A;  // potrf 覆盖下三角
        int64_t info = lapack::potrf( lapack::Uplo::Lower, n, L.data(), n );
        CHECK_MSG( info == 0, "[e2e] potrf: info == 0" );
        for (int j = 0; j < n; ++j)  // 清严格上三角残留（LAPACK 不触碰另一半）
            for (int i = 0; i < j; ++i)
                L[ i + j*n ] = 0.0;
        std::vector<double> LLt( n*n, 0.0 );
        blas::gemm( blas::Layout::ColMajor, blas::Op::NoTrans,
                    blas::Op::Trans, n, n, n,
                    1.0, L.data(), n, L.data(), n, 0.0, LLt.data(), n );
        double potrf_err = 0.0;
        for (int i = 0; i < n*n; ++i)
            potrf_err = std::max( potrf_err, std::abs( LLt[ i ] - A0[ i ] ) );
        CHECK_MSG( potrf_err < 1e-12,
                   "[e2e] potrf: max|L·Lᵀ−A| < 1e-12 (blas::gemm 验算)" );

        // 9.2 posv：A·x = b，b = A·x_true 由 blas::gemv 生成
        std::vector<double> x_true( n );
        for (int i = 0; i < n; ++i)
            x_true[ i ] = 1.0 + frand();
        std::vector<double> b( n, 0.0 );
        blas::gemv( blas::Layout::ColMajor, blas::Op::NoTrans, n, n,
                    1.0, A0.data(), n, x_true.data(), 1, 0.0, b.data(), 1 );
        std::vector<double> X = b;   // posv 覆盖 B 为解
        std::vector<double> AF = A;  // posv 覆盖 A 为分解
        info = lapack::posv( lapack::Uplo::Lower, n, 1, AF.data(), n,
                             X.data(), n );
        CHECK_MSG( info == 0, "[e2e] posv: info == 0" );
        double posv_err = 0.0;
        for (int i = 0; i < n; ++i)
            posv_err = std::max( posv_err, std::abs( X[ i ] - x_true[ i ] ) );
        CHECK_MSG( posv_err < 1e-10, "[e2e] posv: max|x−x_true| < 1e-10" );

        // 9.3 porfs：在 posv 分解上做迭代精化，backward 误差应达机器精度量级
        std::vector<double> ferr( 1 ), berr( 1 );
        info = lapack::porfs( lapack::Uplo::Lower, n, 1,
                              A0.data(), n, AF.data(), n,
                              b.data(), n, X.data(), n,
                              ferr.data(), berr.data() );
        CHECK_MSG( info == 0, "[e2e] porfs: info == 0" );
        CHECK_MSG( berr[ 0 ] < 1e-14, "[e2e] porfs: berr < 1e-14 (机器精度量级)" );

        // 9.4 pocon：条件数估计。dpocon 的入参 A 必须是 Cholesky 因子
        //    （dpotrf/dposv 的输出，即 9.2 的 AF），anorm 才是原阵 A0 的
        //    1-范数（lansy 计算）——两者不可混淆
        double anorm = lapack::lansy( lapack::Norm::One,
                                      lapack::Uplo::Lower, n, A0.data(), n );
        double rcond = 0.0;
        info = lapack::pocon( lapack::Uplo::Lower, n, AF.data(), n,
                              anorm, &rcond );
        CHECK_MSG( info == 0, "[e2e] pocon: info == 0" );
        CHECK_MSG( rcond > 0.0 && rcond <= 1.0, "[e2e] pocon: 0 < rcond ≤ 1" );

        // 9.5 syev / gesvd 独立例程交叉验证：SPD 的奇异值 == 特征值
        //    （注意顺序：dsyev 升序，dgesvd 降序）；pocon 的 rcond 应与
        //    λmin/λmax 同量级（LAPACK 条件数估计器容差，两个数量级内）
        std::vector<double> Aw = A0, w( n );
        info = lapack::syev( lapack::Job::NoVec, lapack::Uplo::Lower,
                             n, Aw.data(), n, w.data() );
        CHECK_MSG( info == 0, "[e2e] syev: info == 0" );
        CHECK_MSG( w.front() > 0.0, "[e2e] syev: λmin > 0 (SPD)" );
        std::vector<double> As = A0, S( n );
        info = lapack::gesvd( lapack::Job::NoVec, lapack::Job::NoVec,
                              n, n, As.data(), n, S.data(),
                              nullptr, 1, nullptr, 1 );
        CHECK_MSG( info == 0, "[e2e] gesvd: info == 0" );
        double sv_err = 0.0;
        for (int i = 0; i < n; ++i)
            sv_err = std::max( sv_err, std::abs( S[ i ] - w[ n-1-i ] ) );
        CHECK_MSG( sv_err < 1e-10 * w.back(),
                   "[e2e] 交叉验证: max|σᵢ−λᵢ| < 1e-10·λmax (gesvd vs syev)" );
        double ratio = w.front() / w.back();  // λmin/λmax
        CHECK_MSG( rcond >= ratio/100.0 && rcond <= ratio*100.0,
                   "[e2e] 交叉验证: rcond 与 λmin/λmax 相差 < 2 个数量级 (pocon vs syev)" );

        // 9.6 全链路残差：精化解的 ‖A·x−b‖₂ 由 blas::nrm2 计算
        std::vector<double> r( n );
        blas::gemv( blas::Layout::ColMajor, blas::Op::NoTrans, n, n,
                    1.0, A0.data(), n, X.data(), 1, 0.0, r.data(), 1 );
        for (int i = 0; i < n; ++i)
            r[ i ] -= b[ i ];
        double resid = blas::nrm2( n, r.data(), 1 );
        CHECK_MSG( resid < 1e-12,
                   "[e2e] 全链路残差: ‖A·x−b‖₂ < 1e-12 (blas::nrm2 验算)" );
    }

    std::printf( "TOTAL assertions=%d\n", g_checks );
    std::printf( g_fail == 0 ? "ALL PASSED\n" : "FAILED: %d\n", g_fail );
    return g_fail == 0 ? 0 : 1;
}
