/* svc_cat.c — inetd-style relay service used by test_micro_inetd.
 *
 * Relays stdin to stdout byte-by-byte (cat semantics) so the test driver
 * can verify that micro_inetd dup2()s the connected socket onto BOTH
 * stdin and stdout of the spawned service process.
 * Exits 0 on EOF — like a well-behaved inetd service.
 */
#include <unistd.h>
#include <stdlib.h>

int main(void)
{
    char buf[4096];
    for (;;) {
        ssize_t n = read(0, buf, sizeof(buf));
        if (n < 0) {
            _exit(1);                 /* read error */
        }
        if (n == 0) {
            _exit(0);                 /* EOF: client closed */
        }
        size_t off = 0;
        while (off < (size_t)n) {
            ssize_t w = write(1, buf + off, (size_t)n - off);
            if (w < 0) {
                _exit(1);             /* write error */
            }
            off += (size_t)w;
        }
    }
}
