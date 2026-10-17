#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <netinet/in.h>

#include <libcidr.h>

static int checks = 0;
static int passed = 0;

#define CHECK(cond, label) do { \
    checks++; \
    if (cond) { \
        passed++; \
        printf("ok %d - %s\n", checks, label); \
    } else { \
        printf("not ok %d - %s\n", checks, label); \
    } \
} while (0)

int main(void) {
    CIDR *c = cidr_from_str("192.168.1.0/24");
    CHECK(c != NULL, "cidr_from_str v4/24");
    CHECK(c != NULL && cidr_get_pflen(c) == 24, "cidr_get_pflen == 24");
    if (c != NULL) {
        char *s = cidr_to_str(c, CIDR_NOFLAGS);
        CHECK(s != NULL && strcmp(s, "192.168.1.0/24") == 0, "cidr_to_str round-trip");
        free(s);
    } else {
        CHECK(0, "cidr_to_str round-trip");
    }

    CIDR *sup = cidr_from_str("192.168.0.0/16");
    CIDR *sub = cidr_from_str("192.168.1.0/24");
    CIDR *other = cidr_from_str("10.0.0.0/8");
    CHECK(sup != NULL && sub != NULL && other != NULL, "parse supernet/subnet/other");
    if (sup && sub && other) {
        CHECK(cidr_contains(sup, sub) == 0, "cidr_contains supernet->subnet");
        CHECK(cidr_equals(sub, sub) == 0, "cidr_equals same block");
        CHECK(cidr_equals(sub, other) != 0, "cidr_equals different blocks");
    } else {
        CHECK(0, "cidr_contains supernet->subnet");
        CHECK(0, "cidr_equals same block");
        CHECK(0, "cidr_equals different blocks");
    }

    CIDR *v6 = cidr_from_str("::1/128");
    CHECK(v6 != NULL && cidr_get_proto(v6) == CIDR_IPV6, "parse v6 ::1/128");
    if (v6 != NULL) {
        char *s6 = cidr_to_str(v6, CIDR_NOFLAGS);
        CHECK(s6 != NULL && strlen(s6) > 0, "cidr_to_str v6 non-empty");
        free(s6);
    } else {
        CHECK(0, "cidr_to_str v6 non-empty");
    }

    CIDR *host = cidr_from_str("192.168.1.77/24");
    if (host != NULL) {
        CIDR *net = cidr_addr_network(host);
        CIDR *bc = cidr_addr_broadcast(host);
        char *nets = net ? cidr_to_str(net, CIDR_NOFLAGS) : NULL;
        char *bcs = bc ? cidr_to_str(bc, CIDR_NOFLAGS) : NULL;
        CHECK(nets != NULL && strcmp(nets, "192.168.1.0/24") == 0, "cidr_addr_network");
        CHECK(bcs != NULL && strcmp(bcs, "192.168.1.255/24") == 0, "cidr_addr_broadcast");
        free(nets);
        free(bcs);
        cidr_free(net);
        cidr_free(bc);
    } else {
        CHECK(0, "cidr_addr_network");
        CHECK(0, "cidr_addr_broadcast");
    }

    struct in_addr ia;
    if (inet_pton(AF_INET, "10.1.2.3", &ia) == 1) {
        CIDR *from_ia = cidr_from_inaddr(&ia);
        CHECK(from_ia != NULL, "cidr_from_inaddr");
        if (from_ia != NULL) {
            struct in_addr back;
            CHECK(cidr_to_inaddr(from_ia, &back) != NULL && memcmp(&back, &ia, sizeof(ia)) == 0,
                  "cidr_to_inaddr round-trip");
            cidr_free(from_ia);
        } else {
            CHECK(0, "cidr_to_inaddr round-trip");
        }
    } else {
        CHECK(0, "cidr_from_inaddr");
        CHECK(0, "cidr_to_inaddr round-trip");
    }

    CHECK(cidr_version() != NULL && strlen(cidr_version()) > 0, "cidr_version non-empty");

    cidr_free(c);
    cidr_free(sup);
    cidr_free(sub);
    cidr_free(other);
    cidr_free(v6);
    cidr_free(host);

    printf("# %d/%d checks passed\n", passed, checks);
    return (passed == checks) ? 0 : 1;
}
