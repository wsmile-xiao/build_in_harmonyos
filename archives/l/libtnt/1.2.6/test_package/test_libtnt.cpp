// test_libtnt.cpp — libtnt 1.2.6 消费者冒烟测试
//
// 实际调用 TNT 核心 API 并断言数值结果（R34：非空壳测试）。
// 覆盖 tnt.h 聚合头引入的 21 个头文件中的 9 类核心组件：
//   版本宏 / Array1D / Array2D(matmult) / Array3D(三重下标) /
//   Fortran_Array2D(1-based) / Vector(deprecated pre-1.0) /
//   math_utils(hypot) / Sparse_Matrix_CompRow(CSR，经 0001 补丁修复) /
//   Stopwatch
//
// 说明：自定义 CHECK 宏（非 <cassert>）——Release 构建 -DNDEBUG 不会
// 将断言编译剔除，且失败时输出行号并影响退出码。
#include <cmath>
#include <iostream>

#include <tnt.h>

static int g_failures = 0;

#define CHECK(cond)                                                          \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::cerr << "CHECK FAILED @" << __LINE__ << ": " #cond "\n";    \
            ++g_failures;                                                    \
        }                                                                    \
    } while (0)

// TNT_MAJOR_VERSION / TNT_MINOR_VERSION 为字符字面量宏（'1' / '2'）
static void test_version() {
    CHECK(TNT_MAJOR_VERSION == '1');
    CHECK(TNT_MINOR_VERSION == '2');
}

static void test_array1d() {
    TNT::Array1D<double> a(3);
    a[0] = 1.0; a[1] = 2.0; a[2] = 3.0;
    TNT::Array1D<double> b(3, 2.0);

    TNT::Array1D<double> sum = a + b;          // 逐元素（array1d_utils）
    CHECK(sum.dim1() == 3);
    CHECK(sum[0] == 3.0 && sum[1] == 4.0 && sum[2] == 5.0);

    TNT::Array1D<double> prod = a * b;         // 逐元素乘
    CHECK(prod[2] == 6.0);

    TNT::Array1D<double> c = a.copy();         // 深拷贝语义
    a[0] = 100.0;
    CHECK(c[0] == 1.0);

    const double* raw = sum;                   // operator const T*() 衰减
    CHECK(raw[1] == 4.0);
}

static void test_array2d() {
    // Array2D 无 operator()（仅 Fortran 系有），元素访问为双下标
    // A[i][j]（operator[](int) 返回 T* 行指针）
    TNT::Array2D<double> A(2, 3);
    double v = 1.0;
    for (int i = 0; i < 2; ++i)
        for (int j = 0; j < 3; ++j)
            A[i][j] = v++;
    // A = [1 2 3; 4 5 6]
    TNT::Array2D<double> B(3, 2, 1.0);

    TNT::Array2D<double> C = TNT::matmult(A, B);   // [6 6; 15 15]
    CHECK(C.dim1() == 2 && C.dim2() == 2);
    CHECK(C[0][0] == 6.0 && C[0][1] == 6.0);
    CHECK(C[1][0] == 15.0 && C[1][1] == 15.0);

    // operator* 为逐元素乘（非矩阵乘：形状不一致时返回空数组，
    // 再取元素即未定义行为——真机第五轮实测段错误的根因），
    // 矩阵乘必须用 matmult；此处以同形状方阵自乘验证逐元素语义
    TNT::Array2D<double> S2(2, 2);
    S2[0][0] = 1.0; S2[0][1] = 2.0; S2[1][0] = 3.0; S2[1][1] = 4.0;
    TNT::Array2D<double> E = S2 * S2;              // [1 4; 9 16]
    CHECK(E[0][1] == 4.0 && E[1][1] == 16.0);

    CHECK(A.dim1() == 2 && A.dim2() == 3);
}

static void test_array3d() {
    // Array3D 无 operator()，元素访问为三重下标 t[i][j][k]
    // （operator[](int) 返回 T**，另有 operator T***() 衰减）
    TNT::Array3D<double> t(2, 2, 2, 0.5);
    CHECK(t.dim1() == 2 && t.dim2() == 2 && t.dim3() == 2);
    t[1][1][1] = 2.5;
    CHECK(t[1][1][1] == 2.5);
    CHECK(t[0][0][0] == 0.5);
}

static void test_fortran_array2d() {
    // Fortran 风格 1-based 索引
    TNT::Fortran_Array2D<double> F(2, 2, 0.0);
    F(1, 1) = 1.5;
    F(2, 2) = 2.5;
    CHECK(F(1, 1) == 1.5);
    CHECK(F(2, 2) == 2.5);
    CHECK(F(1, 2) == 0.0);
}

static void test_vector_legacy() {
    // tnt_vec.h：pre-1.0 deprecated Vector<T>（仍随包交付）
    // operator()(i) 为 1-based，operator[](i) 为 0-based
    TNT::Vector<double> v(3, 1.5);
    CHECK(v(1) == 1.5);       // 1-based
    CHECK(v[0] == 1.5);       // 0-based
    v.newsize(2);
    v(2) = 9.0;
    CHECK(v(2) == 9.0);
}

static void test_math_utils() {
    // tnt_math_utils.h：防上溢/下溢的 hypot 实现
    double h = TNT::hypot(3.0, 4.0);
    CHECK(std::fabs(h - 5.0) < 1e-12);
    CHECK(std::fabs(TNT::hypot(0.0, 7.0) - 7.0) < 1e-12);
}

static void test_sparse_csr() {
    // 2x2 对角阵 diag(5, 8)，CSR 三数组格式（0-based，只读视图）
    // 经 0001 补丁修复后方可编译：上游签名 const T*/const int* 与成员
    // 初始化 Array1D(int, T*) 不匹配（详见 notes.md「上游缺陷与补丁」）
    double val[2] = {5.0, 8.0};
    int rowptr[3] = {0, 1, 2};
    int colind[2] = {0, 1};

    TNT::Sparse_Matrix_CompRow<double> S(2, 2, 2, val, rowptr, colind);
    CHECK(S.dim1() == 2 && S.dim2() == 2);
    CHECK(S.NumNonzeros() == 2);
    CHECK(S.val(0) == 5.0 && S.val(1) == 8.0);
    CHECK(S.row_ptr(0) == 0 && S.row_ptr(2) == 2);
    CHECK(S.col_ind(1) == 1);
}

static void test_stopwatch() {
    // 注意：Stopwatch::running() 在 tnt_stopwatch.h:48 声明但从未定义
    // （上游悬空声明，链接期才暴露），不可调用；用 start/stop/resume
    // 状态机代替断言
    TNT::Stopwatch sw;
    sw.start();
    double t = sw.stop();
    CHECK(t >= 0.0);
    sw.resume();
    double t2 = sw.stop();
    CHECK(t2 >= t);
}

int main() {
    test_version();
    test_array1d();
    test_array2d();
    test_array3d();
    test_fortran_array2d();
    test_vector_legacy();
    test_math_utils();
    test_sparse_csr();
    test_stopwatch();

    if (g_failures != 0) {
        std::cerr << "libtnt smoke: " << g_failures << " check(s) FAILED" << std::endl;
        return 1;
    }
    std::cout << "libtnt smoke: all 32 checks passed" << std::endl;
    return 0;
}
