// test_package/test.cpp — consumer smoke test for libprimecount.
// Exercises the public C API declared in <primecount.h>:
//   primecount_version(), primecount_pi(x), primecount_nth_prime(n).
#include <primecount.h>
#include <cstdio>
#include <cstdint>

int main(void) {
    const char *ver = primecount_version();
    // pi(100)  = 25   (primes <= 100)
    // pi(1000) = 168  (primes <= 1000)
    // nth_prime(1) = 2 (first prime)
    int64_t pi100  = primecount_pi(100);
    int64_t pi1000 = primecount_pi(1000);
    int64_t p1     = primecount_nth_prime(1);

    if (ver && pi100 == 25 && pi1000 == 168 && p1 == 2) {
        printf("primecount %s: pi(100)=%lld pi(1000)=%lld nth_prime(1)=%lld OK\n",
               ver, (long long)pi100, (long long)pi1000, (long long)p1);
        return 0;
    }
    printf("FAIL: ver=%s pi(100)=%lld pi(1000)=%lld nth_prime(1)=%lld\n",
           ver ? ver : "(null)", (long long)pi100, (long long)pi1000, (long long)p1);
    return 1;
}
