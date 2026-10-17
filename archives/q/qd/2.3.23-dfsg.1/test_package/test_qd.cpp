#include <cmath>
#include <cstdio>

#include <qd/c_qd.h>
#include <qd/dd_real.h>
#include <qd/fpu.h>
#include <qd/qd_real.h>

static int failures = 0;

static void check(bool ok, const char *what) {
  std::printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
  if (!ok) {
    ++failures;
  }
}

int main(void) {
  fpu_fix_start(nullptr);

  /* 1. Double-double precision: the (1/3)*3 roundtrip error must stay below
   * one dd_real eps (2^-104). Plain double arithmetic fails this check
   * (error ~1.1e-16). */
  dd_real dd_third = dd_real(1.0) / dd_real(3.0);
  dd_real dd_err = abs(dd_third * dd_real(3.0) - dd_real(1.0));
  check(to_double(dd_err) < dd_real::_eps,
        "dd_real (1/3)*3 roundtrip error < 2^-104");

  /* 2. Quad-double precision: the same roundtrip must stay below one qd_real
   * eps (2^-209). Double-double arithmetic fails this check (~4.9e-32). */
  qd_real qd_third = qd_real(1.0) / qd_real(3.0);
  qd_real qd_err = abs(qd_third * qd_real(3.0) - qd_real(1.0));
  check(to_double(qd_err) < qd_real::_eps,
        "qd_real (1/3)*3 roundtrip error < 2^-209");

  /* 3. Exact eps fingerprint of the installed dd_real. */
  check(dd_real::_eps == 4.93038065763132e-32,
        "dd_real::_eps == 2^-104 fingerprint");

  /* 4. Exact eps fingerprint of the installed qd_real. */
  check(qd_real::_eps == 1.21543267145725e-63,
        "qd_real::_eps == 2^-209 fingerprint");

  /* 5. Pi digits through the C++ quad-double interface. */
  double pi_err = std::fabs(to_double(qd_real::_pi) - 3.141592653589793);
  check(pi_err < 1.0e-15, "qd_real::_pi agrees with pi to double digits");

  /* 6. C interface c_qd_pi: leading component is pi and the second quad-double
   * component is a genuine non-zero correction term. */
  double p[4];
  c_qd_pi(p);
  bool c_ok = std::fabs(p[0] - 3.141592653589793) < 1.0e-15 &&
              p[1] != 0.0 && std::fabs(p[1]) < 1.0e-15;
  check(c_ok, "c_qd_pi returns pi with non-zero second component");

  fpu_fix_end(nullptr);

  std::printf("qd API assertions: %d passed\n", 6 - failures);
  return failures == 0 ? 0 : 1;
}
