/*
 * test_package for opendmarc 1.4.2
 *
 * R34: must exercise the packaged library API.  This consumer test links
 * against libopendmarc and calls the DMARC record parser:
 *   - opendmarc_policy_library_init()
 *   - opendmarc_policy_connect_init()
 *   - opendmarc_policy_parse_dmarc()   (valid record -> DMARC_PARSE_OKAY)
 *   - opendmarc_policy_parse_dmarc()   (empty record  -> DMARC_PARSE_ERROR_EMPTY)
 *   - opendmarc_policy_connect_shutdown()
 *   - opendmarc_policy_library_shutdown()
 */
#include <stdio.h>
#include <string.h>

#include <opendmarc/dmarc.h>

int main(void)
{
	OPENDMARC_LIB_T lib;
	DMARC_POLICY_T *pctx;
	int rc;
	int failures = 0;

	memset(&lib, 0, sizeof lib);
	if (opendmarc_policy_library_init(&lib) != 0) {
		fprintf(stderr, "FAIL: opendmarc_policy_library_init\n");
		return 1;
	}

	pctx = opendmarc_policy_connect_init((u_char *)"192.0.2.1", 0);
	if (pctx == NULL) {
		fprintf(stderr, "FAIL: opendmarc_policy_connect_init\n");
		opendmarc_policy_library_shutdown(&lib);
		return 1;
	}

	/* 1) A well-formed DMARC record must parse as OKAY. */
	rc = opendmarc_policy_parse_dmarc(
		pctx,
		(u_char *)"example.com",
		(u_char *)"v=DMARC1; p=reject; rua=mailto:dmarc@example.com");
	if (rc != DMARC_PARSE_OKAY) {
		fprintf(stderr, "FAIL: valid record rc=%d (expected %d)\n",
			rc, DMARC_PARSE_OKAY);
		failures++;
	} else {
		printf("PASS: valid DMARC record parsed (rc=%d)\n", rc);
	}

	/* 2) An empty record must be rejected as EMPTY. */
	rc = opendmarc_policy_parse_dmarc(pctx, (u_char *)"example.com",
					  (u_char *)"");
	if (rc != DMARC_PARSE_ERROR_EMPTY) {
		fprintf(stderr, "FAIL: empty record rc=%d (expected %d)\n",
			rc, DMARC_PARSE_ERROR_EMPTY);
		failures++;
	} else {
		printf("PASS: empty record rejected (rc=%d)\n", rc);
	}

	/* 3) A bad version token must be rejected. */
	rc = opendmarc_policy_parse_dmarc(pctx, (u_char *)"example.com",
					  (u_char *)"v=DMARC9; p=none");
	if (rc != DMARC_PARSE_ERROR_BAD_VERSION) {
		fprintf(stderr, "FAIL: bad version rc=%d (expected %d)\n",
			rc, DMARC_PARSE_ERROR_BAD_VERSION);
		failures++;
	} else {
		printf("PASS: bad version rejected (rc=%d)\n", rc);
	}

	opendmarc_policy_connect_shutdown(pctx);
	opendmarc_policy_library_shutdown(&lib);

	if (failures != 0) {
		fprintf(stderr, "test_package: %d assertion(s) failed\n", failures);
		return 1;
	}
	printf("test_package: all assertions passed\n");
	return 0;
}
