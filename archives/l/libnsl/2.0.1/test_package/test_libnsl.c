/*
 * HarmonyOS PC consumer test for libnsl 2.0.1.
 *
 * Links the public libnsl::libnsl CMake target (and transitively
 * libtirpc::libtirpc) and exercises the parts of the public NIS API that are
 * decidable without a live NIS server:
 *
 *   1. yperr_string()      - the 17-entry NIS status table
 *   2. ypbinderr_string()  - the 5-entry ypbind status table
 *   3. ypprot_err()        - NIS wire status -> YP status mapping
 *   4. yp_get_default_domain() - contract: YPERR_SUCCESS iff *domain != NULL
 *   5. xdr_domainname()    - real XDR encode/decode round trip through an
 *                            in-memory stream, which only works if the
 *                            libtirpc dependency is resolved at runtime
 *
 * The process exit code is the PASS/FAIL signal (0 = all checks passed).
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include <rpc/rpc.h>
#include <rpcsvc/ypclnt.h>
#include <rpcsvc/yp_prot.h>

static int checks = 0;
static int failures = 0;

static void check_str(const char *what, const char *got, const char *want)
{
    checks++;
    if (got == NULL) {
        printf("FAIL %-34s got NULL, want \"%s\"\n", what, want);
        failures++;
        return;
    }
    if (strcmp(got, want) != 0) {
        printf("FAIL %-34s got \"%s\", want \"%s\"\n", what, got, want);
        failures++;
        return;
    }
    printf("ok   %-34s \"%s\"\n", what, got);
}

static void check_int(const char *what, int got, int want)
{
    checks++;
    if (got != want) {
        printf("FAIL %-34s got %d, want %d\n", what, got, want);
        failures++;
        return;
    }
    printf("ok   %-34s %d\n", what, got);
}

static void check_true(const char *what, int cond)
{
    checks++;
    if (!cond) {
        printf("FAIL %-34s condition false\n", what);
        failures++;
        return;
    }
    printf("ok   %-34s true\n", what);
}

int main(void)
{
    char buf[512];
    XDR xdrs;
    char *encode_me;
    char *decoded = NULL;
    char *domain = (char *)0x1; /* poison: libnsl must overwrite this */
    int rc;

    printf("libnsl consumer test (HarmonyOS PC / aarch64)\n");
    printf("--------------------------------------------\n");

    /* 1. yperr_string() - exact upstream table (see src/yperr_string.c) */
    check_str("yperr_string(SUCCESS)", yperr_string(YPERR_SUCCESS), "Success");
    check_str("yperr_string(BADARGS)", yperr_string(YPERR_BADARGS), "Request arguments bad");
    check_str("yperr_string(RPC)", yperr_string(YPERR_RPC), "RPC failure on NIS operation");
    check_str("yperr_string(DOMAIN)", yperr_string(YPERR_DOMAIN),
              "Can't bind to server which serves this domain");
    check_str("yperr_string(MAP)", yperr_string(YPERR_MAP), "No such map in server's domain");
    check_str("yperr_string(KEY)", yperr_string(YPERR_KEY), "No such key in map");
    check_str("yperr_string(YPERR)", yperr_string(YPERR_YPERR), "Internal NIS error");
    check_str("yperr_string(RESRC)", yperr_string(YPERR_RESRC),
              "Local resource allocation failure");
    check_str("yperr_string(NOMORE)", yperr_string(YPERR_NOMORE),
              "No more records in map database");
    check_str("yperr_string(PMAP)", yperr_string(YPERR_PMAP),
              "Can't communicate with portmapper");
    check_str("yperr_string(YPBIND)", yperr_string(YPERR_YPBIND),
              "Can't communicate with ypbind");
    check_str("yperr_string(YPSERV)", yperr_string(YPERR_YPSERV),
              "Can't communicate with ypserv");
    check_str("yperr_string(NODOM)", yperr_string(YPERR_NODOM),
              "Local domain name not set");
    check_str("yperr_string(BADDB)", yperr_string(YPERR_BADDB), "NIS map database is bad");
    check_str("yperr_string(VERS)", yperr_string(YPERR_VERS),
              "NIS client/server version mismatch - can't supply service");
    check_str("yperr_string(ACCESS)", yperr_string(YPERR_ACCESS), "Permission denied");
    check_str("yperr_string(BUSY)", yperr_string(YPERR_BUSY), "Database is busy");
    check_str("yperr_string(unknown)", yperr_string(4242), "Unknown NIS error code");

    /* 2. ypbinderr_string() - exact upstream table (src/ypbinderr_string.c) */
    check_str("ypbinderr_string(0)", ypbinderr_string(0), "Success");
    check_str("ypbinderr_string(ERR)", ypbinderr_string(YPBIND_ERR_ERR),
              "Internal ypbind error");
    check_str("ypbinderr_string(NOSERV)", ypbinderr_string(YPBIND_ERR_NOSERV),
              "Domain not bound");
    check_str("ypbinderr_string(RESC)", ypbinderr_string(YPBIND_ERR_RESC),
              "System resource allocation failure");
    check_str("ypbinderr_string(NODOMAIN)", ypbinderr_string(YPBIND_ERR_NODOMAIN),
              "Domain doesn't exist");
    check_str("ypbinderr_string(unknown)", ypbinderr_string(4242), "Unknown ypbind error");

    /* 3. ypprot_err() - wire status -> YP status mapping (src/ypprot_err.c).
     *    Out-of-range wire statuses must collapse to YPERR_YPERR. */
    check_int("ypprot_err(YP_TRUE)", ypprot_err(YP_TRUE), YPERR_SUCCESS);
    check_int("ypprot_err(YP_NOMORE)", ypprot_err(YP_NOMORE), YPERR_NOMORE);
    check_int("ypprot_err(YP_NOMAP)", ypprot_err(YP_NOMAP), YPERR_MAP);
    check_int("ypprot_err(YP_NODOM)", ypprot_err(YP_NODOM), YPERR_DOMAIN);
    check_int("ypprot_err(YP_NOKEY)", ypprot_err(YP_NOKEY), YPERR_KEY);
    check_int("ypprot_err(YP_BADDB)", ypprot_err(YP_BADDB), YPERR_BADDB);
    check_int("ypprot_err(YP_BADARGS)", ypprot_err(YP_BADARGS), YPERR_BADARGS);
    check_int("ypprot_err(YP_VERS)", ypprot_err(YP_VERS), YPERR_VERS);
    check_int("ypprot_err(0)=YP_FALSE", ypprot_err(0), YPERR_YPERR);
    check_int("ypprot_err(99) too large", ypprot_err(99), YPERR_YPERR);
    check_int("ypprot_err(-100) too small", ypprot_err(-100), YPERR_YPERR);

    /* 4. yp_get_default_domain() - must never crash and must honour its
     *    contract: YPERR_SUCCESS <=> a non-NULL domain is returned. */
    rc = yp_get_default_domain(&domain);
    check_true("yp_get_default_domain rc valid",
               rc == YPERR_SUCCESS || rc == YPERR_NODOM);
    check_true("yp_get_default_domain contract",
               (rc == YPERR_SUCCESS && domain != NULL) ||
               (rc == YPERR_NODOM && domain == NULL));
    if (rc == YPERR_SUCCESS) {
        check_true("yp_get_default_domain non-empty",
                   domain != NULL && domain[0] != '\0');
    } else {
        printf("note yp_get_default_domain: no domain configured (YPERR_NODOM)\n");
    }

    /* 5. xdr_domainname() - real encode/decode round trip. This exercises
     *    libnsl's XDR encoder against libtirpc's xdrmem_create/xdr_getpos, so
     *    a stale or missing libtirpc would fail to link or corrupt the value. */
    memset(buf, 0, sizeof(buf));
    encode_me = (char *)"example.nis.domain"; /* 18 chars -> 20 padded */
    xdrmem_create(&xdrs, buf, sizeof(buf), XDR_ENCODE);
    check_true("xdr_domainname encode", xdr_domainname(&xdrs, &encode_me) == TRUE);
    /* XDR variable-length opaque/string = 4-byte length + data padded to 4. */
    check_true("xdr_domainname advanced stream",
               (unsigned long)xdr_getpos(&xdrs) ==
                   (unsigned long)(4 + ((strlen(encode_me) + 3UL) & ~3UL)));
    xdr_destroy(&xdrs);

    xdrmem_create(&xdrs, buf, sizeof(buf), XDR_DECODE);
    check_true("xdr_domainname decode", xdr_domainname(&xdrs, &decoded) == TRUE);
    xdr_destroy(&xdrs);
    check_str("xdr_domainname round trip", decoded, "example.nis.domain");
    free(decoded);

    printf("--------------------------------------------\n");
    printf("checks=%d failures=%d\n", checks, failures);
    if (failures == 0) {
        printf("RESULT: PASS (%d/%d)\n", checks, checks);
        return 0;
    }
    printf("RESULT: FAIL (%d/%d)\n", checks - failures, checks);
    return 1;
}
