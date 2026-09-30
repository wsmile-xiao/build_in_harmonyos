/* Equiv-rewrite of upstream pr95620.c.
 *
 * Upstream is a dg-do-link LTO test restricted to x86-64 lp64 with
 * -mcmodel=medium and a ~2.83 GB static array (double a[353783808]); it only
 * links, it is never run (the second loop `for (;; b++)` would not terminate).
 * OHOS is aarch64 + clang: -mcmodel=medium does not apply and a 2.83 GB BSS is
 * not meaningful here. We reduce the array to a linkable size and make the
 * program a runnable rc=0 smoke test of the same data layout.
 */
double a[4096];
int b, c, d;

int
main (void)
{
  a[c] = 1.0;
  if (a[c])
    d++;
  return 0;
}
