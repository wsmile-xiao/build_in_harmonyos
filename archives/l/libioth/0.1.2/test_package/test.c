#include <ioth.h>
#include <iothaddr.h>

#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>

/* Consumer test for libioth 0.1.2 (R34: really exercises the library).
 * Covers both shipped libraries without needing a vde switch or root:
 * - libioth: native-stack lifecycle (newstack/msocket/socket/close,
 *   defstack get/set, delstack) using the kernel stack (real fds).
 * - libiothaddr: deterministic hash/mac/eui64 vectors derived from the
 *   documented md5("test.v2.cs.unibo.it") = 69d62fac095a5a2ee4c2c79f211e57e3:
 *   hashmac takes H[0]:H[1]:H[2]:H[5]:H[6]:H[7] then forces locally-admin
 *   unicast (byte0 |= 0x02, &= ~0x01), so 0x69 -> 0x6a and the true mac is
 *   6a:d6:2f:5a:5a:2e (the header doc example prints the pre-adjustment
 *   69:... value).
 * TAP-style output: each CHECK prints "ok N name" or "not ok N name".
 * The test_package conanfile counts the "ok" lines (13 checks total).
 */
static int g_n = 0;

#define CHECK(cond, name)                               \
    do {                                                \
        ++g_n;                                          \
        if (!(cond)) {                                  \
            printf("not ok %d %s\n", g_n, name);        \
            return 1;                                   \
        }                                               \
        printf("ok %d %s\n", g_n, name);                \
    } while (0)

int main(void)
{
    /* Unbuffered TAP output: if the binary is killed (timeout/OOM) the
     * already-printed "ok" lines must survive in the log for diagnosis. */
    setvbuf(stdout, NULL, _IONBF, 0);

    /* T1: native stack needs no plugin and no network: empty stack name
     * selects the kernel stack, NULL vnl means no virtual interface. */
    struct ioth *stack = ioth_newstack(NULL, NULL);
    CHECK(stack != NULL, "newstack-native");

    /* T2: default stack is initially the kernel native stack. */
    CHECK(ioth_get_defstack() != NULL, "get-defstack-native");

    /* T3: installing our stack as default routes ioth_socket() to it. */
    ioth_set_defstack(stack);
    CHECK(ioth_get_defstack() == stack, "set-defstack");

    /* T4/T5: real socket creation through the selected stacks. */
    int fd1 = ioth_msocket(stack, AF_INET, SOCK_STREAM, 0);
    CHECK(fd1 >= 0, "msocket-inet-stream");
    int fd2 = ioth_socket(AF_INET, SOCK_STREAM, 0);
    CHECK(fd2 >= 0, "socket-default-stack");

    /* T6/T7: closing returns the fds and drops the stack use count. */
    CHECK(ioth_close(fd1) == 0, "close-msocket-fd");
    CHECK(ioth_close(fd2) == 0, "close-socket-fd");

    /* T8: hash-based MAC vector. md5("test.v2.cs.unibo.it") =
     * 69d62fac095a5a2ee4c2c79f211e57e3; hashmac takes
     * H[0]:H[1]:H[2]:H[5]:H[6]:H[7] then sets locally-admin unicast
     * (byte0 |= 0x02, &= ~0x01): 0x69 -> 0x6b -> 0x6a. */
    unsigned char mac[6];
    iothaddr_hashmac(mac, "test.v2.cs.unibo.it", NULL);
    unsigned char expect_mac[6] = {0x6a, 0xd6, 0x2f, 0x5a, 0x5a, 0x2e};
    CHECK(memcmp(mac, expect_mac, sizeof(mac)) == 0, "hashmac-vector");

    /* T9a: macton parses the printed form back (return value). */
    unsigned char parsed[6];
    CHECK(ioth_macton("6a:d6:2f:5a:5a:2e", parsed) == 1, "macton-parse");
    /* T9b: parsed bytes equal the expected MAC. */
    CHECK(memcmp(parsed, expect_mac, sizeof(parsed)) == 0, "macton-bytes");

    /* T10: ntomac renders the bytes back to the canonical string. */
    char macstr[MAC_ADDRSTRLEN];
    ioth_ntomac(expect_mac, macstr, sizeof(macstr));
    CHECK(strcmp(macstr, "6a:d6:2f:5a:5a:2e") == 0, "ntomac-string");

    /* T11: hasheui64 == eui64(hashmac): same name feeds both paths, the
     * resulting interface identifiers must agree. */
    struct in6_addr base;
    memset(&base, 0, sizeof(base));
    base.s6_addr[0] = 0x20; base.s6_addr[1] = 0x00;
    base.s6_addr[2] = 0x07; base.s6_addr[3] = 0x60;
    struct in6_addr a1 = base, a2 = base;
    iothaddr_hasheui64(&a1, "test.v2.cs.unibo.it", NULL);
    unsigned char mac2[6];
    iothaddr_hashmac(mac2, "test.v2.cs.unibo.it", NULL);
    iothaddr_eui64(&a2, mac2);
    CHECK(memcmp(&a1, &a2, sizeof(a1)) == 0, "hasheui64-consistency");

    /* T12: deleting the stack releases it; restore the native default. */
    ioth_set_defstack(NULL);
    CHECK(ioth_delstack(stack) == 0, "delstack");

    printf("libioth consumer test passed\n");
    return 0;
}
