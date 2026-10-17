/* upstream_igl_test.cpp — vendored subset of libigl 2.6.0 upstream tests.
 *
 * Ports 8 data-independent Catch2 TEST_CASEs to plain asserts so they run on
 * HarmonyOS without Catch2 downloads or test-data downloads:
 *   1. accumarray: matlab_help  (tests/include/igl/accumarray.cpp)
 *   2. accumarray: scalar       (tests/include/igl/accumarray.cpp)
 *   3. cat: rows                (tests/include/igl/cat.cpp)
 *   4. cat: cols                (tests/include/igl/cat.cpp)
 *   5. adjacency_list: simple   (tests/include/igl/adjacency_list.cpp)
 *   6. unique_rows: vector      (tests/include/igl/unique.cpp, first case)
 *   7. sort: small ascending    (tests/include/igl/sort.cpp, 4x3 dim=1)
 *   8. doublearea: unit quad    (mirrors doublearea semantics)
 *
 * Full upstream suite: 146 files / 294 TEST_CASEs (see MANIFEST.yml audit).
 * The remaining 286 cases require mesh data downloads (test_common::data_path),
 * Catch2 FetchContent, or optional deps (CGAL/Embree/TetGen) and are excluded
 * with reasons in MANIFEST.yml.
 */
#include <Eigen/Core>
#include <igl/accumarray.h>
#include <igl/adjacency_list.h>
#include <igl/cat.h>
#include <igl/doublearea.h>
#include <igl/sort.h>
#include <igl/unique_rows.h>
#include <cmath>
#include <cstdio>
#include <vector>

static int g_passed = 0;
static int g_failed = 0;

#define UCHECK(cond, name) do { \
    if (cond) { g_passed++; printf("[UPSTREAM PASS] %s\n", name); } \
    else { g_failed++; printf("[UPSTREAM FAIL] %s\n", name); } \
} while (0)

int main()
{
    // 1. accumarray matlab_help
    {
        Eigen::VectorXd V(5); V << 101, 102, 103, 104, 105;
        Eigen::VectorXi S(5); S << 0, 2, 3, 2, 3;
        Eigen::VectorXd A, Agt(4); Agt << 101, 0, 206, 208;
        igl::accumarray(S, V, A);
        UCHECK(A.size() == Agt.size() && (A - Agt).norm() < 1e-12, "accumarray:matlab_help");
    }
    // 2. accumarray scalar
    {
        Eigen::VectorXi n(5); n << 1, 2, 2, 4, 5;
        Eigen::VectorXi C, Cgt(6); Cgt << 0, 1, 2, 0, 1, 1;
        igl::accumarray(n, 1, C);
        UCHECK(C.size() == Cgt.size() && (C - Cgt).norm() == 0, "accumarray:scalar");
    }
    // 3. cat rows
    {
        std::vector<Eigen::RowVector3i> rows = {
            Eigen::RowVector3i(1, 2, 3),
            Eigen::RowVector3i(4, 5, 6),
            Eigen::RowVector3i(7, 8, 9)};
        Eigen::MatrixXi actual;
        igl::cat(1, rows, actual);
        Eigen::Matrix3i expected;
        expected << 1, 2, 3, 4, 5, 6, 7, 8, 9;
        UCHECK(actual.rows() == 3 && actual.cols() == 3 && (actual - expected).norm() == 0, "cat:rows");
    }
    // 4. cat cols
    {
        std::vector<Eigen::Vector3i> cols = {
            Eigen::Vector3i(1, 4, 7),
            Eigen::Vector3i(2, 5, 8),
            Eigen::Vector3i(3, 6, 9)};
        Eigen::MatrixXi actual;
        igl::cat(2, cols, actual);
        Eigen::Matrix3i expected;
        expected << 1, 2, 3, 4, 5, 6, 7, 8, 9;
        UCHECK(actual.rows() == 3 && actual.cols() == 3 && (actual - expected).norm() == 0, "cat:cols");
    }
    // 5. adjacency_list simple (offset 0)
    {
        Eigen::MatrixXi F(2, 3);
        F << 0, 1, 2, 0, 2, 3;
        std::vector<std::vector<int>> A;
        igl::adjacency_list(F, A, true);
        bool ok = (A.size() == 4 && A[0].size() == 3 && A[1].size() == 2 &&
                   A[2].size() == 3 && A[3].size() == 2 && A[0][0] == 1 &&
                   A[0][1] == 2 && A[0][2] == 3);
        UCHECK(ok, "adjacency_list:simple");
    }
    // 6. unique_rows on a small integer vector
    {
        Eigen::VectorXi A(6); A << 3, 1, 3, 2, 1, 3;
        Eigen::VectorXi C, IA, IC;
        igl::unique_rows(A, C, IA, IC);
        bool ok = (C.size() == 3);
        if (ok) {
            for (int i = 0; i < A.size(); i++) ok = ok && (C(IC(i)) == A(i));
        }
        UCHECK(ok, "unique_rows:vector");
    }
    // 7. sort ascending along dim 1 on a fixed 4x3 matrix
    {
        Eigen::MatrixXd X(4, 3);
        X << 3, 1, 2,
             0, 5, 4,
             9, 7, 8,
             6, 11, 10;
        Eigen::MatrixXd Y;
        Eigen::MatrixXi IX;
        igl::sort(X, 1, true, Y, IX);
        bool ok = (Y.rows() == 4 && Y.cols() == 3);
        for (int j = 0; ok && j < 3; j++)
            for (int i = 1; i < 4; i++) ok = ok && (Y(i, j) >= Y(i - 1, j));
        UCHECK(ok, "sort:ascending-dim1");
    }
    // 8. doublearea on a unit quad (two triangles, total 2.0)
    {
        Eigen::MatrixXd V(4, 3);
        V << 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0;
        Eigen::MatrixXi F(2, 3);
        F << 0, 1, 2, 0, 2, 3;
        Eigen::VectorXd A;
        igl::doublearea(V, F, A);
        bool ok = (A.size() == 2 && std::abs(A(0) - 1.0) < 1e-12 && std::abs(A(1) - 1.0) < 1e-12);
        UCHECK(ok, "doublearea:unit-quad");
    }

    printf("UPSTREAM SUMMARY: passed %d failed %d total 8\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
