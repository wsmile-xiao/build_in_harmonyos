/*
 * test.c — libatm consumer test for OpenHarmony / HarmonyOS.
 *
 * Exercises the public libatm API (text2atm/atm2text/sap_equal) and the two
 * atmpvc/atmsvc_addr_in_use() helpers that the OHOS build restores, and makes
 * sure <sys/socket.h> and <linux/atm.h> can be used together (on OHOS both try
 * to define struct sockaddr_storage).
 */
#include <stdio.h>
#include <string.h>

#include <sys/socket.h>		/* defines struct sockaddr_storage on OHOS */
#include <linux/atm.h>		/* must NOT redefine it */
#include <linux/atmsap.h>

#include <atm.h>
#include <atmsap.h>

static int failures;

static void check(int ok, const char *what)
{
    if (ok) {
	printf("ok: %s\n", what);
    } else {
	printf("FAIL: %s\n", what);
	failures++;
    }
}

int main(void)
{
    struct sockaddr_atmpvc pvc, empty;
    struct atm_sap sap_a, sap_b;
    struct sockaddr_storage ss;
    char text[MAX_ATM_ADDR_LEN];

    /* 1. text2atm(): parse a PVC address */
    memset(&pvc, 0, sizeof(pvc));
    check(text2atm("0.0.5", (struct sockaddr *) &pvc, sizeof(pvc), T2A_PVC) == 0,
	  "text2atm(\"0.0.5\") succeeds");
    check(pvc.sap_addr.itf == 0 && pvc.sap_addr.vpi == 0 && pvc.sap_addr.vci == 5,
	  "text2atm() decoded itf=0 vpi=0 vci=5");

    /* 2. atm2text(): round-trip back to text */
    check(atm2text(text, sizeof(text), (struct sockaddr *) &pvc, 0) > 0,
	  "atm2text() succeeds");
    check(!strcmp(text, "0.0.5"), "atm2text() round-trips to \"0.0.5\"");

    /* 3. helpers restored in <atm.h> for OHOS */
    check(atmpvc_addr_in_use(pvc) != 0, "atmpvc_addr_in_use() true for 0.0.5");
    memset(&empty, 0, sizeof(empty));
    check(atmpvc_addr_in_use(empty) == 0, "atmpvc_addr_in_use() false for empty");

    /* 4. sap_equal() goes through blli_in_use() inside libatm */
    memset(&sap_a, 0, sizeof(sap_a));
    memset(&sap_b, 0, sizeof(sap_b));
    check(sap_equal(&sap_a, &sap_b, SXE_COMPATIBLE) != 0,
	  "sap_equal() finds two empty SAPs compatible");

    /* 5. <sys/socket.h> and <linux/atm.h> coexist (no sockaddr_storage clash) */
    memset(&ss, 0, sizeof(ss));
    check(sizeof(ss) >= sizeof(sa_family_t), "sockaddr_storage usable with linux/atm.h");

    printf("linux-atm libatm consumer test: %s (%d failure(s))\n",
	   failures ? "FAILED" : "PASSED", failures);
    return failures ? 1 : 0;
}
