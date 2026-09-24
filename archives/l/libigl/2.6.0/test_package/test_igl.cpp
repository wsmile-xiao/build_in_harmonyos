/* test_igl.cpp — libigl 2.6.0 consumer test (HarmonyOS PC).
 *
 * 6 real geometry checks on synthetic meshes (no data downloads):
 *   1. cotmatrix on a single triangle: 3x3, symmetric, zero row sum
 *   2. massmatrix (barycentric) on the same triangle: total mass == area
 *   3. per_face_normals on a unit square: both normals +Z
 *   4. doublearea on the unit right triangle: 1.0 (area 0.5)
 *   5. edge_lengths on the unit right triangle: 1, 1, sqrt(2)
 *   6. adjacency_list on a quad (2 triangles): vertex degrees 3,2,3,2
 */
#include <Eigen/Core>
#include <Eigen/Sparse>
#include <igl/adjacency_list.h>
#include <igl/cotmatrix.h>
#include <igl/doublearea.h>
#include <igl/edge_lengths.h>
#include <igl/massmatrix.h>
#include <igl/per_face_normals.h>
#include <cmath>
#include <cstdio>

static int g_passed = 0;
static int g_failed = 0;

#define CHECK(cond, fmt, ...) do { \
    if (cond) { g_passed++; printf("[PASS] " fmt "\n", ##__VA_ARGS__); } \
    else { g_failed++; printf("[FAIL] " fmt "\n", ##__VA_ARGS__); } \
} while (0)

int main()
{
    Eigen::MatrixXd V(3, 3);
    V << 0.0, 0.0, 0.0,
         1.0, 0.0, 0.0,
         0.0, 1.0, 0.0;
    Eigen::MatrixXi F(1, 3);
    F << 0, 1, 2;

    // 1. cotangent Laplacian
    {
        Eigen::SparseMatrix<double> L;
        igl::cotmatrix(V, F, L);
        CHECK(L.rows() == 3 && L.cols() == 3, "cotmatrix size 3x3");
        Eigen::MatrixXd Ld(L);
        double asym = (Ld - Ld.transpose()).norm();
        CHECK(asym < 1e-12, "cotmatrix symmetric (asym=%.3e)", asym);
        Eigen::VectorXd ones = Eigen::VectorXd::Ones(3);
        double rowsum = (Ld * ones).norm();
        CHECK(rowsum < 1e-12, "cotmatrix zero row sum (%.3e)", rowsum);
    }

    // 2. mass matrix: sum of entries equals triangle area (0.5)
    {
        Eigen::SparseMatrix<double> M;
        igl::massmatrix(V, F, igl::MASSMATRIX_TYPE_BARYCENTRIC, M);
        double total = M.sum();
        CHECK(std::abs(total - 0.5) < 1e-12, "massmatrix total mass %.12f ~= 0.5", total);
    }

    // 3. per-face normals on a unit square in the XY plane
    {
        Eigen::MatrixXd Vs(4, 3);
        Vs << 0, 0, 0,
              1, 0, 0,
              1, 1, 0,
              0, 1, 0;
        Eigen::MatrixXi Fs(2, 3);
        Fs << 0, 1, 2,
              0, 2, 3;
        Eigen::MatrixXd N;
        igl::per_face_normals(Vs, Fs, N);
        bool ok = (N.rows() == 2) &&
                  (std::abs(N(0, 0)) < 1e-12 && std::abs(N(0, 1)) < 1e-12 && std::abs(N(0, 2) - 1.0) < 1e-12) &&
                  (std::abs(N(1, 0)) < 1e-12 && std::abs(N(1, 1)) < 1e-12 && std::abs(N(1, 2) - 1.0) < 1e-12);
        CHECK(ok, "per_face_normals both +Z");
    }

    // 4. doublearea of the unit right triangle
    {
        Eigen::VectorXd A;
        igl::doublearea(V, F, A);
        CHECK(A.size() == 1 && std::abs(A(0) - 1.0) < 1e-12, "doublearea %.12f ~= 1.0", A.size() ? A(0) : -1.0);
    }

    // 5. edge lengths: 1, 1, sqrt(2)
    {
        Eigen::MatrixXd L;
        igl::edge_lengths(V, F, L);
        bool ok = (L.rows() == 1 && L.cols() == 3);
        if (ok) {
            double l0 = L(0, 0), l1 = L(0, 1), l2 = L(0, 2);
            // igl orders opposite edges: e0 opposite v0 (between v1,v2) = sqrt2
            double s2 = std::sqrt(2.0);
            ok = (std::abs(l0 - s2) < 1e-12 && std::abs(l1 - 1.0) < 1e-12 && std::abs(l2 - 1.0) < 1e-12);
            CHECK(ok, "edge_lengths %.6f %.6f %.6f", l0, l1, l2);
        } else {
            CHECK(false, "edge_lengths matrix shape %dx%d", (int)L.rows(), (int)L.cols());
        }
    }

    // 6. adjacency list on a quad
    {
        Eigen::MatrixXi Fq(2, 3);
        Fq << 0, 1, 2,
              0, 2, 3;
        std::vector<std::vector<int>> Ab;
        igl::adjacency_list(Fq, Ab, true);
        bool ok = (Ab.size() == 4 && Ab[0].size() == 3 && Ab[1].size() == 2 &&
                   Ab[2].size() == 3 && Ab[3].size() == 2);
        CHECK(ok, "adjacency_list degrees 3,2,3,2");
    }

    printf("CONSUMER SUMMARY: passed %d failed %d\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}
