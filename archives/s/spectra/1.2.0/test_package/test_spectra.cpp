// test_spectra.cpp — L1 smoke test for spectra header-only library
// 验证 spectra 头文件可用，且能正确计算对称矩阵的特征值
#include <algorithm>
#include <iostream>
#include <vector>
#include <Eigen/Core>
#include <Eigen/Eigenvalues>
#include <Spectra/SymEigsSolver.h>
#include <Spectra/MatOp/DenseSymMatProd.h>

int main() {
    // 构造一个 6x6 对称矩阵 (循环拉普拉斯矩阵)
    const int n = 6;
    Eigen::MatrixXd M = Eigen::MatrixXd::Zero(n, n);
    for (int i = 0; i < n; i++) {
        M(i, i) = 1.0;
        M(i, (i + n - 1) % n) = -0.5;
        M(i, (i + 1) % n) = -0.5;
    }

    // 使用 Spectra 计算最大的 2 个特征值
    Spectra::DenseSymMatProd<double> op(M);
    Spectra::SymEigsSolver<Spectra::DenseSymMatProd<double>> eigs(op, 2, 4);
    eigs.init();
    eigs.compute(Spectra::SortRule::LargestMagn);

    // Test 1: 验证计算成功
    if (eigs.info() != Spectra::CompInfo::Successful) {
        std::cerr << "FAIL: 特征值计算失败" << std::endl;
        return 1;
    }

    Eigen::VectorXd evals = eigs.eigenvalues();
    std::cout << "Spectra 计算的特征值 (最大的 2 个):\n" << evals << std::endl;

    // Test 2: 用 Eigen 完整求解器交叉验证
    Eigen::SelfAdjointEigenSolver<Eigen::MatrixXd> es(M);
    Eigen::VectorXd true_evals = es.eigenvalues();
    std::cout << "Eigen 参考特征值 (全部):\n" << true_evals << std::endl;

    // 统一排序后再比较 (Spectra 按 LargestMagn 排序, Eigen 按升序排列)
    std::vector<double> spectra_vals(evals.data(), evals.data() + evals.size());
    std::vector<double> eigen_top2(true_evals.data() + (n - 2), true_evals.data() + n);
    std::sort(spectra_vals.begin(), spectra_vals.end());
    std::sort(eigen_top2.begin(), eigen_top2.end());

    double diff = 0.0;
    for (int i = 0; i < 2; i++) {
        diff = std::max(diff, std::abs(spectra_vals[i] - eigen_top2[i]));
    }
    std::cout << "最大误差: " << diff << std::endl;

    // Test 3: 验证误差在可接受范围内
    if (diff > 1e-9) {
        std::cerr << "FAIL: 特征值误差 " << diff << " 超过 1e-9" << std::endl;
        return 1;
    }

    std::cout << "PASS: spectra 特征值计算正确" << std::endl;
    return 0;
}
