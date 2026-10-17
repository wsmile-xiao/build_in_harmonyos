/* test_visa.c -- consumer test for librevisa (VISA instrument control).
 *
 * Exercises 5 deterministic public APIs; no hardware needed:
 *   1. viOpenDefaultRM must return VI_SUCCESS with a non-null session.
 *   2. viParseRsrc("GPIB0::1::INSTR") must return VI_SUCCESS (the 20130812
 *      snapshot implements it as a stub that always succeeds without
 *      filling the outputs, so only the return code is asserted).
 *   3. viGetAttribute(RM_SESSION) on the resource manager must return
 *      VI_SUCCESS with VI_NULL (see resource_manager::GetAttribute).
 *   4. viGetAttribute(RSRC_NAME) on the resource manager must return
 *      VI_SUCCESS with an empty string.
 *   5. viClose on the resource manager must return VI_SUCCESS.
 * A failing check prints to stderr and exits 1 (R34: real API calls).
 *
 * NOTE: viStatusDesc is declared in visa.h and exported in libvisa.sym
 * but has NO implementation in the 0.0.20130812 snapshot (no
 * viStatusDesc.cpp in src/, not listed in src/Makefile.am), so this
 * test must not call it -- linking would fail with
 * "undefined symbol: viStatusDesc". Only APIs with real implementations
 * are exercised here.
 */
#include <stdio.h>

#include <visa.h>

int main(void)
{
    ViSession rm = VI_NULL;
    ViStatus rc;

    /* 1. Open the default resource manager. */
    rc = viOpenDefaultRM(&rm);
    if (rc != VI_SUCCESS) {
        fprintf(stderr, "FAIL check1: viOpenDefaultRM rc=%d\n", (int)rc);
        return 1;
    }
    if (rm == VI_NULL) {
        fprintf(stderr, "FAIL check1: viOpenDefaultRM returned VI_NULL\n");
        return 1;
    }
    printf("ok check1: viOpenDefaultRM succeeded\n");

    /* 2. Parse a resource string (stub: only the return code is defined). */
    {
        ViUInt16 intfType = 0;
        ViUInt16 intfNum = 0xFFFF;
        rc = viParseRsrc(rm, (ViRsrc)"GPIB0::1::INSTR", &intfType, &intfNum);
        if (rc != VI_SUCCESS) {
            fprintf(stderr, "FAIL check2: viParseRsrc rc=%d\n", (int)rc);
            viClose(rm);
            return 1;
        }
        printf("ok check2: viParseRsrc returned VI_SUCCESS\n");
    }

    /* 3. RM_SESSION attribute of the resource manager is VI_NULL. */
    {
        ViSession sess = (ViSession)0x1234;
        rc = viGetAttribute(rm, VI_ATTR_RM_SESSION, &sess);
        if (rc != VI_SUCCESS) {
            fprintf(stderr, "FAIL check3: viGetAttribute(RM_SESSION) rc=%d\n",
                    (int)rc);
            viClose(rm);
            return 1;
        }
        if (sess != VI_NULL) {
            fprintf(stderr, "FAIL check3: RM_SESSION != VI_NULL\n");
            viClose(rm);
            return 1;
        }
        printf("ok check3: VI_ATTR_RM_SESSION == VI_NULL\n");
    }

    /* 4. RSRC_NAME attribute of the resource manager is empty. */
    {
        ViChar name[256];
        unsigned i;
        for (i = 0; i < sizeof(name); ++i)
            name[i] = (ViChar)0x7F;
        rc = viGetAttribute(rm, VI_ATTR_RSRC_NAME, name);
        if (rc != VI_SUCCESS) {
            fprintf(stderr, "FAIL check4: viGetAttribute(RSRC_NAME) rc=%d\n",
                    (int)rc);
            viClose(rm);
            return 1;
        }
        if (name[0] != '\0') {
            fprintf(stderr, "FAIL check4: RSRC_NAME not empty\n");
            viClose(rm);
            return 1;
        }
        printf("ok check4: VI_ATTR_RSRC_NAME is empty\n");
    }

    rc = viClose(rm);
    if (rc != VI_SUCCESS) {
        fprintf(stderr, "FAIL check5: viClose rc=%d\n", (int)rc);
        return 1;
    }
    printf("ok check5: viClose succeeded\n");

    printf("test_visa: all 5 checks passed\n");
    return 0;
}
