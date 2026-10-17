// Consumer test — libecpint 1.0.7 (R34: real packaged-library API use).
//
// Reproduces the first block of the upstream tests/lib/int_test1
// benchmark through the installed package: an ECP on center A with five
// primitives, two Gaussian shells, ECPIntegral(3, 4), and
// compute_shell_pair(newU, shellA, shellA). The 9 benchmark values
// (lines 1-9 of tests/lib/int_test1/test1.output, upstream tarball
// sha256 e9c60fdd...) are compared element-wise at 1e-7, well inside
// the upstream check_file threshold of 1e-5. Also verifies that the
// generated config.hpp (LIBECPINT_MAX_L) is installed with the package.
#include <libecpint/api.hpp>
#include <libecpint/config.hpp>
#include <libecpint/ecp.hpp>
#include <libecpint/ecpint.hpp>
#include <libecpint/gshell.hpp>
#include <libecpint/multiarr.hpp>

#include <cmath>
#include <cstdio>
#include <vector>

namespace {

// tests/lib/int_test1/test1.output lines 1-9 (shell pair A,A).
const double kBenchmark[9] = {
    0.0739240924526688, 0.0, 0.0,
    0.0, 0.0739240924526688, 0.0,
    0.0, 0.0, 0.0739240924526688,
};

int failures = 0;

void check(bool ok, const char *what) {
  if (!ok) {
    std::printf("FAIL: %s\n", what);
    ++failures;
  } else {
    std::printf("ok: %s\n", what);
  }
}

}  // namespace

int main() {
  using namespace libecpint;

  double A[3] = {0.5, 1.5, 0.9};
  double B[3] = {-0.5, -0.5, -0.5};
  ECP newU(A);
  newU.addPrimitive(2, 4, 1.0, 0.0);
  newU.addPrimitive(2, 0, 2.015185434, 0.437903605);
  newU.addPrimitive(2, 1, 1.225772391, 0.418499875);
  newU.addPrimitive(2, 2, 3.415601371, 10.482661239);
  newU.addPrimitive(2, 3, 3.574403408, -4.478284427, true);

  GaussianShell shellA(A, 1);
  GaussianShell shellB(B, 3);
  shellA.addPrim(0.15, 0.3);
  shellA.addPrim(2.49, 0.9);
  shellA.addPrim(10.11, 1.2);
  shellB.addPrim(0.02, 1.1);
  shellB.addPrim(1.41, 0.9);
  shellB.addPrim(8.71, 0.4);

  ECPIntegral ecpint(3, 4);
  TwoIndex<double> result;
  ecpint.compute_shell_pair(newU, shellA, shellA, result);

  std::vector<double> flat;
  flat.reserve(result.data.size());
  for (auto v : result.data) flat.push_back(v);

  check(flat.size() == 9, "shell pair (A,A) yields 9 integrals");
  if (flat.size() == 9) {
    bool diag_ok = true, offdiag_ok = true;
    for (int i = 0; i < 9; ++i) {
      const bool diagonal = (i % 4) == 0;  // indices 0, 4, 8
      if (diagonal) {
        if (std::fabs(flat[i] - kBenchmark[i]) > 1e-7) diag_ok = false;
      } else {
        if (std::fabs(flat[i] - kBenchmark[i]) > 1e-7) offdiag_ok = false;
      }
    }
    check(diag_ok, "diagonal integrals match upstream benchmark (1e-7)");
    check(offdiag_ok, "off-diagonal integrals match upstream benchmark (1e-7)");
  }

#if defined(LIBECPINT_MAX_L)
  check(LIBECPINT_MAX_L == 5, "installed config.hpp exposes LIBECPINT_MAX_L=5");
#else
  check(false, "installed config.hpp exposes LIBECPINT_MAX_L=5");
#endif

  if (failures == 0) {
    std::printf("ALL CONSUMER CHECKS PASSED\n");
    return 0;
  }
  std::printf("%d CONSUMER CHECK(S) FAILED\n", failures);
  return 1;
}
