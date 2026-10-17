#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include "cryptopANT.h"

static int checks = 0;
static int passed = 0;
#define ASSERT(cond, msg) do { checks++; if (cond) { passed++; printf("[PASS] %s\n", msg); } else { printf("[FAIL] %s\n", msg); fprintf(stderr, "FAILED: %s at %s:%d\n", msg, __FILE__, __LINE__); exit(1); } } while(0)

int main(void) {
    // 1. name<->type round trip
    ASSERT(scramble_name2type("aes") == SCRAMBLE_AES, "name2type aes");
    ASSERT(scramble_name2type("blowfish") == SCRAMBLE_BLOWFISH, "name2type blowfish");
    ASSERT(strcmp(scramble_type2name(SCRAMBLE_AES), "aes") == 0, "type2name aes");
    ASSERT(strcmp(scramble_type2name(SCRAMBLE_MD5), "md5") == 0, "type2name md5");

    // 2. init with deterministic AES state
    unsigned char pad[32], key[16], mac[8], iv[16];
    memset(pad, 0x42, sizeof(pad));
    memset(key, 0x11, sizeof(key));
    memset(mac, 0, sizeof(mac));
    memset(iv, 0, sizeof(iv));
    scramble_state_t st;
    st.c4 = SCRAMBLE_AES;
    st.c6 = SCRAMBLE_AES;
    st.pad = pad; st.plen = sizeof(pad);
    st.key = key; st.klen = sizeof(key);
    st.mac = mac; st.mlen = 0; // no mac
    st.iv = iv; st.ivlen = sizeof(iv);
    int r = scramble_init(&st);
    ASSERT(r == 0, "scramble_init AES");

    // 3. ipv4 scramble / unscramble round trip
    uint32_t orig4 = inet_addr("1.2.3.4"); // network order
    uint32_t anon4 = scramble_ip4(orig4, 0);
    // anon should differ (except class preservation edge)
    // For 1.2.3.4 (class A) first bit preserved, but rest should change
    // At least not equal for this key
    // We don't assert not equal strictly (could theoretically equal), just check round-trip
    uint32_t dean4 = unscramble_ip4(anon4, 0);
    ASSERT(dean4 == orig4, "ipv4 round-trip 1.2.3.4");

    // 4. prefix-preserving: same /24 should share prefix
    uint32_t ip_a = inet_addr("192.168.1.1");
    uint32_t ip_b = inet_addr("192.168.1.2");
    uint32_t anon_a = scramble_ip4(ip_a, 0);
    uint32_t anon_b = scramble_ip4(ip_b, 0);
    // /24 prefix preserving => first 24 bits of anon_a and anon_b share same masked diff from orig
    // Check descramble still works
    ASSERT(unscramble_ip4(anon_a, 0) == ip_a, "ipv4 prefix test descramble A");
    ASSERT(unscramble_ip4(anon_b, 0) == ip_b, "ipv4 prefix test descramble B");

    // 5. ipv6 scramble / descramble
    struct in6_addr orig6, anon6, tmp6;
    inet_pton(AF_INET6, "fe80::21e:c9ff:feaa:bbbb", &orig6);
    anon6 = orig6;
    scramble_ip6(&anon6, 0);
    // anon should differ
    tmp6 = anon6;
    unscramble_ip6(&tmp6, 0);
    ASSERT(memcmp(&tmp6, &orig6, sizeof(orig6)) == 0, "ipv6 round-trip fe80::");

    // 6. cleanup lifecycle
    scramble_cleanup();
    // re-init should still work after cleanup
    st.c4 = SCRAMBLE_SHA1; st.c6 = SCRAMBLE_SHA1;
    ASSERT(scramble_init(&st) == 0, "re-init SHA1 after cleanup");
    uint32_t anon_sha = scramble_ip4(orig4, 0);
    ASSERT(unscramble_ip4(anon_sha, 0) == orig4, "ipv6 SHA1 round-trip still works");
    scramble_cleanup();

    printf("All %d/%d checks passed\n", passed, checks);
    // HMBS marker is emitted by conanfile.py, but also print a sanity line
    return 0;
}
