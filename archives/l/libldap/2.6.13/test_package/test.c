#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <ldap.h>
#include <lber.h>

static int failures = 0;
static int passes = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (line %d): %s\n", __func__, __LINE__, msg); \
        failures++; \
        return 1; \
    } \
} while (0)

#define PASS(msg) do { printf("PASS: %s: %s\n", __func__, msg); passes++; } while (0)

/* 1: ldap_create / set_option / get_option / unbind_ext */
static int test_ldap_create(void) {
    LDAP *ld = NULL;
    int ver = 0;
    int rc = ldap_create(&ld);
    CHECK(rc == LDAP_SUCCESS && ld != NULL, "ldap_create");
    rc = ldap_set_option(ld, LDAP_OPT_PROTOCOL_VERSION, &(int){LDAP_VERSION3});
    CHECK(rc == LDAP_SUCCESS, "ldap_set_option PROTOCOL_VERSION");
    rc = ldap_get_option(ld, LDAP_OPT_PROTOCOL_VERSION, &ver);
    CHECK(rc == LDAP_SUCCESS && ver == LDAP_VERSION3, "ldap_get_option PROTOCOL_VERSION");
    ldap_unbind_ext(ld, NULL, NULL);
    PASS("ldap_create/set/get/unbind");
    return 0;
}

/* 2: LDAP_OPT_API_INFO */
static int test_api_info(void) {
    LDAPAPIInfo api;
    api.ldapai_info_version = LDAP_API_INFO_VERSION;
    int rc = ldap_get_option(NULL, LDAP_OPT_API_INFO, &api);
    CHECK(rc == LDAP_SUCCESS, "ldap_get_option API_INFO");
    CHECK(api.ldapai_info_version == LDAP_API_INFO_VERSION, "api version mismatch");
    CHECK(api.ldapai_api_version == LDAP_API_VERSION, "api_version");
    PASS("LDAP_OPT_API_INFO");
    return 0;
}

/* 3: ldap_url_parse / ldap_free_urldesc / ldap_is_ldap_url */
static int test_url_parse(void) {
    const char *url = "ldap://localhost:389/dc=example,dc=com?cn,sn?sub?(objectClass=*)";
    CHECK(ldap_is_ldap_url(url) != 0, "ldap_is_ldap_url true");
    CHECK(ldap_is_ldap_url("http://example.com") == 0, "ldap_is_ldap_url false for http");
    LDAPURLDesc *lud = NULL;
    int rc = ldap_url_parse(url, &lud);
    CHECK(rc == LDAP_URL_SUCCESS && lud != NULL, "ldap_url_parse");
    CHECK(lud->lud_host && strcmp(lud->lud_host, "localhost") == 0, "lud_host");
    CHECK(lud->lud_port == 389, "lud_port");
    CHECK(lud->lud_dn && strcmp(lud->lud_dn, "dc=example,dc=com") == 0, "lud_dn");
    CHECK(lud->lud_scope == LDAP_SCOPE_SUBTREE, "lud_scope sub");
    CHECK(lud->lud_filter && strcmp(lud->lud_filter, "(objectClass=*)") == 0, "lud_filter");
    /* attrs */
    CHECK(lud->lud_attrs && lud->lud_attrs[0] && strcmp(lud->lud_attrs[0], "cn") == 0, "lud_attrs[0]");
    CHECK(lud->lud_attrs[1] && strcmp(lud->lud_attrs[1], "sn") == 0, "lud_attrs[1]");
    /* round-trip via desc2str */
    char *ustr = ldap_url_desc2str(lud);
    CHECK(ustr != NULL && strstr(ustr, "ldap://") != NULL, "ldap_url_desc2str");
    ldap_memfree(ustr);
    ldap_free_urldesc(lud);
    PASS("ldap_url_parse/free/desc2str");
    return 0;
}

/* 4: ldap_str2dn / ldap_dn2str / ldap_dnfree */
static int test_dn(void) {
    const char *dn_str = "cn=John Doe,dc=example,dc=com";
    LDAPDN dn = NULL;
    int rc = ldap_str2dn(dn_str, &dn, LDAP_DN_FORMAT_LDAPV3);
    CHECK(rc == LDAP_SUCCESS && dn != NULL, "ldap_str2dn");
    char *out = NULL;
    rc = ldap_dn2str(dn, &out, LDAP_DN_FORMAT_LDAPV3);
    CHECK(rc == LDAP_SUCCESS && out != NULL, "ldap_dn2str");
    /* normalized output contains cn and dc components (case-insensitive check not needed) */
    CHECK(strstr(out, "cn=") != NULL || strstr(out, "CN=") != NULL, "dn2str contains cn");
    CHECK(strstr(out, "dc=example") != NULL, "dn2str contains dc");
    ldap_memfree(out);
    ldap_dnfree(dn);
    PASS("ldap_str2dn/dn2str/dnfree");
    return 0;
}

/* 5: ldap_err2string */
static int test_err2string(void) {
    const char *s = ldap_err2string(LDAP_SUCCESS);
    CHECK(s != NULL && strlen(s) > 0, "ldap_err2string SUCCESS");
    s = ldap_err2string(LDAP_INVALID_DN_SYNTAX);
    CHECK(s != NULL && strlen(s) > 0, "ldap_err2string INVALID_DN_SYNTAX");
    PASS("ldap_err2string");
    return 0;
}

/* 6: liblber encode (ber_alloc_t / ber_printf / ber_flatten2 / ber_free)
 * 注意：bv 在栈上，须用 ber_memfree(bv.bv_val) 释放，不能 ber_bvfree(&bv)（后者会 free 栈结构导致 SIGSEGV）*/
static int test_ber_encode(void) {
    BerElement *ber = ber_alloc_t(LBER_USE_DER);
    CHECK(ber != NULL, "ber_alloc_t");
    int rc = ber_printf(ber, "{si}", "hello", 42);
    CHECK(rc >= 0, "ber_printf {si}");
    struct berval bv;
    bv.bv_val = NULL;
    bv.bv_len = 0;
    rc = ber_flatten2(ber, &bv, 1);
    CHECK(rc == 0 && bv.bv_val != NULL && bv.bv_len > 0, "ber_flatten2");
    CHECK((unsigned char)bv.bv_val[0] == 0x30, "BER SEQUENCE tag");
    ber_memfree(bv.bv_val);
    ber_free(ber, 1);
    PASS("lber ber_alloc/printf/flatten/free");
    return 0;
}

int main(void) {
    printf("=== libldap 2.6.13 consumer tests (offline, no slapd) ===\n");
    printf("vendor: %s version %d\n", LDAP_VENDOR_NAME, LDAP_VENDOR_VERSION);

    test_ldap_create();
    test_api_info();
    test_url_parse();
    test_dn();
    test_err2string();
    test_ber_encode();

    printf("--- summary: %d passed, %d failed ---\n", passes, failures);
    if (failures) {
        fprintf(stderr, "test libldap 2.6.13: FAIL (%d failures)\n", failures);
        return 1;
    }
    printf("test libldap 2.6.13: OK (vendor version %d)\n", LDAP_VENDOR_VERSION);
    return 0;
}
