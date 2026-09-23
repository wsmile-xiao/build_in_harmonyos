/* Unbuffered stdio for the libstuff test runner (test binary only).
 *
 * The upstream harness (libstuff_test/test.c) prints via printf without
 * ever flushing stdout. When stdout is a pipe it is fully buffered, so if
 * the runner dies from a signal every byte of harness output is lost and
 * the failure is undiagnosable. This translation unit is linked into the
 * libstuff_test_runner binary ONLY (never into mtoc): its constructor
 * forces unbuffered stdio before main() runs. No test assertion, test
 * count, or library behavior is changed.
 */
#include <stdio.h>

__attribute__((constructor))
static void
ocmtoc_test_unbuffer(void)
{
    setvbuf(stdout, (char *)0, _IONBF, 0);
    setvbuf(stderr, (char *)0, _IONBF, 0);
}
