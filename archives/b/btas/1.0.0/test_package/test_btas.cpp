// test_btas.cpp — real consumer test for the btas/1.0.0 Conan package.
//
// Compiles and runs against the packaged headers (btas + boost from the
// Conan graph) exactly like a downstream OHOS consumer would:
//   1. generated btas/version.h content,
//   2. feature auto-detection (__has_include) and default index type,
//   3. core tensor algebra on the generic (non-BLAS) backend:
//      scal / axpy / dot / gemm / contract,
//   4. TensorView round-trip (make_view reflects writes into the base).
// Every check prints a PASS line; the program exits non-zero on failure.
#include <btas/btas.h>
#include <btas/tensor.h>
#include <btas/tensorview.h>
#include <btas/version.h>

#include <boost/container/small_vector.hpp>

#include <cmath>
#include <complex>
#include <cstdio>
#include <string>

using DTensor = btas::Tensor<double>;
using ZTensor = btas::Tensor<std::complex<double>>;

namespace {

int g_checks = 0;
int g_failures = 0;

#define BTAS_TP_CHECK(cond)                                                    \
  do {                                                                         \
    ++g_checks;                                                                \
    if (cond) {                                                                \
      std::printf("PASS %2d: %s\n", g_checks, #cond);                          \
    } else {                                                                   \
      ++g_failures;                                                            \
      std::printf("FAIL %2d: %s  (%s:%d)\n", g_checks, #cond, __FILE__,        \
                  __LINE__);                                                   \
    }                                                                          \
  } while (0)

// fill T with T(i,j,...) = 1ij (matches the upstream unittest convention;
// works for real and complex element types)
template <typename T>
void fill_els(T& t) {
  if (t.rank() == 0) return;
  const double base = std::pow(10.0, static_cast<double>(t.rank()));
  const std::size_t max_ii = t.rank() - 1;
  for (auto i : t.range()) {
    double val = base;
    for (std::size_t ii = 0; ii <= max_ii; ++ii) {
      val += i[ii] * std::pow(10.0, static_cast<double>(max_ii - ii));
    }
    t(i) = val;
  }
}

}  // namespace

int main() {
  // ---- 1. generated version header ------------------------------------
  BTAS_TP_CHECK(std::string(BTAS_VERSION) == "1.0.0");
  BTAS_TP_CHECK(BTAS_MAJOR_VERSION == 1 && BTAS_MINOR_VERSION == 0 &&
                BTAS_MICRO_VERSION == 0);

  // ---- 2. feature detection / default index type -----------------------
#ifdef BTAS_IS_USABLE
  BTAS_TP_CHECK(BTAS_IS_USABLE == 1);
#else
  BTAS_TP_CHECK(false && "BTAS_IS_USABLE not defined");
#endif
#ifdef BTAS_HAS_BOOST_CONTAINER
  BTAS_TP_CHECK(BTAS_HAS_BOOST_CONTAINER == 1);
#else
  BTAS_TP_CHECK(false && "BTAS_HAS_BOOST_CONTAINER not detected");
#endif
  BTAS_TP_CHECK(BTAS_TARGET_MAX_INDEX_RANK == 6);
  static_assert(
      std::is_same<btas::DEFAULT::index_type,
                   boost::container::small_vector<long, 6>>::value,
      "default index type must be boost::container::small_vector<long, 6>");

  // ---- 3. generic backend tensor algebra -------------------------------
  DTensor a(2, 2);
  fill_els(a);
  BTAS_TP_CHECK(a.rank() == 2 && a.extent(0) == 2 && a.extent(1) == 2);
  BTAS_TP_CHECK(a.range().area() == 4);

  // scal: a <- 2*a   (fill convention, rank 2: a(0,0)=100, a(1,1)=111)
  btas::scal(2.0, a);
  BTAS_TP_CHECK(a(0, 0) == 2.0 * 100.0 && a(1, 1) == 2.0 * 111.0);

  // axpy: b <- 1*a + b
  DTensor b(2, 2);
  fill_els(b);
  btas::axpy(1.0, a, b);
  BTAS_TP_CHECK(std::abs(b(0, 0) - (200.0 + 100.0)) < 1e-12 &&
                std::abs(b(1, 1) - (222.0 + 111.0)) < 1e-12);
  const DTensor& c = b;

  // dot: <a, b> against a manual reduction
  {
    const auto d = btas::dot(a, b);
    double manual = 0.0;
    for (auto i : a.range()) manual += a(i) * b(i);
    BTAS_TP_CHECK(std::abs(d - manual) < 1e-12);
  }

  // gemm: m = a(2,2) * k(2,3) against manual loops
  DTensor k(2, 3);
  fill_els(k);
  DTensor m(2, 3);
  btas::gemm(blas::Op::NoTrans, blas::Op::NoTrans, 1.0, a, k, 0.0, m);
  {
    bool ok = true;
    for (std::size_t r = 0; r < 2 && ok; ++r) {
      for (std::size_t col = 0; col < 3; ++col) {
        double val = 0.0;
        for (std::size_t n = 0; n < 2; ++n) val += a(r, n) * k(n, col);
        if (std::abs(m(r, col) - val) > 1e-12) { ok = false; break; }
      }
    }
    BTAS_TP_CHECK(ok && "gemm matches manual matrix product");
  }

  // contract: c2(i,l) = sum_j a2(i,j) * k2(j,l) against manual loops
  DTensor a2(2, 3);
  DTensor k2(3, 2);
  fill_els(a2);
  fill_els(k2);
  enum { i, j, l };
  DTensor c2;
  btas::contract(1.0, a2, {i, j}, k2, {j, l}, 0.0, c2, {i, l});
  {
    bool ok = c2.rank() == 2 && c2.extent(0) == 2 && c2.extent(1) == 2;
    for (std::size_t r = 0; r < 2 && ok; ++r) {
      for (std::size_t col = 0; col < 2; ++col) {
        double val = 0.0;
        for (std::size_t n = 0; n < 3; ++n) val += a2(r, n) * k2(n, col);
        if (std::abs(c2(r, col) - val) > 1e-12) { ok = false; break; }
      }
    }
    BTAS_TP_CHECK(ok && "contract matches manual contraction");
  }

  // complex tensor path: scal on ZTensor
  ZTensor z(2, 2, 2);
  fill_els(z);
  const std::complex<double> zref = z(1, 1, 1);
  btas::scal(std::complex<double>(0.0, 1.0), z);
  BTAS_TP_CHECK(std::abs(z(1, 1, 1) - std::complex<double>(0.0, 1.0) * zref) <
                1e-12);

  // ---- 4. TensorView round-trip ----------------------------------------
  DTensor t0(2, 3);
  fill_els(t0);
  auto t0v = btas::make_view(t0);
  t0v(0, 0) = 777.0;
  BTAS_TP_CHECK(t0(0, 0) == 777.0 && t0v.extent(0) == 2 &&
                t0v.extent(1) == 3);

  // ---- summary ----------------------------------------------------------
  std::printf("btas/1.0.0 consumer test: %d checks, %d failures\n", g_checks,
              g_failures);
  std::printf("BTAS_VERSION=%s\n", BTAS_VERSION);
  return g_failures == 0 ? 0 : 1;
}
