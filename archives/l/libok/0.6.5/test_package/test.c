#include <stdio.h>
#include "ok.h"

/*
 * Consumer test: links against the installed libok (public header +
 * public API only) and verifies a real TAP session with observable
 * output: expect 2 successes, emit 2 ok() assertions, then check
 * ok_done() reports success.  Explicit if-checks (not assert) so the
 * verification survives Release (-DNDEBUG) builds.
 */
int main(void) {
  ok_expect(2);
  ok("consumer beep");
  ok("consumer boop");
  if (ok_count() != 2 || ok_failed() != 0) {
    fprintf(stderr, "libok consumer test FAILED: count=%d failed=%d\n",
            ok_count(), ok_failed());
    return 1;
  }
  if (ok_done() != true) {
    fprintf(stderr, "libok consumer test FAILED: ok_done() != true\n");
    return 1;
  }
  return 0;
}
