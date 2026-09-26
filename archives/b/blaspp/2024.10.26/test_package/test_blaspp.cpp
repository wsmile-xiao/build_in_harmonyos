// blaspp 2024.10.26 消费者验证（鸿蒙侧 test_package）
// 用上游公开 C++ API 做数值断言：version / axpy / dot / gemm / nrm2。
#include <blas.hh>

#include <cmath>
#include <cstdio>
#include <vector>

static int g_fail = 0;

#define CHECK_MSG(cond, msg)                                    \
    do {                                                        \
        if (cond) {                                             \
            std::printf("ok   %s\n", msg);                      \
        } else {                                                \
            std::printf("FAIL %s\n", msg);                      \
            ++g_fail;                                           \
        }                                                       \
    } while (0)

int main()
{
    // 1. 版本断言：宏与运行时函数一致，均为 2024.10.26
    CHECK_MSG( BLASPP_VERSION == 20241026, "BLASPP_VERSION == 20241026" );
    CHECK_MSG( blas::blaspp_version() == 20241026, "blaspp_version() == 20241026" );

    // 2. axpy：y = alpha*x + y，x=[1,2,3], y=[4,5,6], alpha=2 → y=[6,9,12]
    {
        std::vector<double> x = { 1.0, 2.0, 3.0 };
        std::vector<double> y = { 4.0, 5.0, 6.0 };
        blas::axpy( 3, 2.0, x.data(), 1, y.data(), 1 );
        bool ok = std::abs( y[0] - 6.0 ) < 1e-12
               && std::abs( y[1] - 9.0 ) < 1e-12
               && std::abs( y[2] - 12.0 ) < 1e-12;
        CHECK_MSG( ok, "axpy: y = 2*x + y" );
    }

    // 3. dot：x·y = 1*4 + 2*5 + 3*6 = 32
    {
        std::vector<double> x = { 1.0, 2.0, 3.0 };
        std::vector<double> y = { 4.0, 5.0, 6.0 };
        double d = blas::dot( 3, x.data(), 1, y.data(), 1 );
        CHECK_MSG( std::abs( d - 32.0 ) < 1e-12, "dot(x,y) == 32" );
    }

    // 4. gemm：C = 1.0*A*B + 1.0*C，A=[[1,2],[3,4]]，B=[[5,6],[7,8]]
    //    → C_prev=0 时 C=[[19,22],[43,50]]
    {
        std::vector<double> A = { 1.0, 2.0, 3.0, 4.0 };  // row-major 2x2
        std::vector<double> B = { 5.0, 6.0, 7.0, 8.0 };
        std::vector<double> C = { 0.0, 0.0, 0.0, 0.0 };
        blas::gemm( blas::Layout::RowMajor, blas::Op::NoTrans, blas::Op::NoTrans,
                    2, 2, 2, 1.0, A.data(), 2, B.data(), 2, 1.0, C.data(), 2 );
        bool ok = std::abs( C[0] - 19.0 ) < 1e-12 && std::abs( C[1] - 22.0 ) < 1e-12
               && std::abs( C[2] - 43.0 ) < 1e-12 && std::abs( C[3] - 50.0 ) < 1e-12;
        CHECK_MSG( ok, "gemm row-major 2x2" );
    }

    // 5. nrm2：||[3,4]|| = 5
    {
        std::vector<double> x = { 3.0, 4.0 };
        double n = blas::nrm2( 2, x.data(), 1 );
        CHECK_MSG( std::abs( n - 5.0 ) < 1e-12, "nrm2([3,4]) == 5" );
    }

    std::printf( g_fail == 0 ? "ALL PASSED\n" : "FAILED: %d\n", g_fail );
    return g_fail == 0 ? 0 : 1;
}
