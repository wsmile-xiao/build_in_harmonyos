/*
 * test_package/test.c — smoke test source for cc65
 *
 * Minimal C program compiled by cc65 during test_package to verify
 * that the cc65 binary can actually compile C code (R34: test must
 * exercise the tested package's binary, not just check --version).
 *
 * Invoked by test.sh as:  cc65 -c test.c
 * Produces test.s (6502 assembly) on success.
 */
int main(void)
{
    return 0;
}
