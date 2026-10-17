/*
 * Adaptation tests for libcapi20 3.27 on OpenHarmony.
 *
 * Upstream 3.27 ships no test suite at all (Makefile.am has no TESTS target and
 * there is no test directory), so every case below was added by the adaptation.
 *
 * The cases are deliberately device independent: a HarmonyOS PC has no CAPI
 * kernel driver, while the CAPI 2.0 message codec and the capi20ext* accessors
 * are fully usable - and therefore verifiable - without one.  The last case pins
 * down the documented behaviour of the library when no driver/module is
 * reachable, which is the situation on this platform.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <capi20.h>
#include <capiutils.h>
#include <capicmd.h>

static int g_total;
static int g_failed;

static void check(int ok, const char *name)
{
	g_total++;
	if (ok) {
		printf("PASS %s\n", name);
	} else {
		g_failed++;
		printf("FAIL %s\n", name);
	}
}

/* Case 1: header setup + CAPI 2.0 wire encoding + decoding round trip. */
static void case_cmsg_codec_roundtrip(void)
{
	_cmsg cmsg;
	_cmsg decoded;
	unsigned char msg[2048];
	unsigned len;
	unsigned rc;

	memset(&cmsg, 0, sizeof(cmsg));
	rc = capi_cmsg_header(&cmsg, 0x0101, CAPI_ALERT, CAPI_REQ, 0x0042, 0x00000000);
	check(rc == CapiNoError, "cmsg_codec_header_build");

	rc = capi_cmsg2message(&cmsg, msg);
	check(rc == CapiNoError, "cmsg_codec_encode");

	len = (unsigned)msg[0] | ((unsigned)msg[1] << 8);
	check(msg[4] == CAPI_ALERT && msg[5] == CAPI_REQ,
	      "cmsg_codec_wire_command_bytes");
	check(len >= CAPI_MSG_BASELEN, "cmsg_codec_wire_length");

	memset(&decoded, 0, sizeof(decoded));
	rc = capi_message2cmsg(&decoded, msg);
	check(rc == CapiNoError, "cmsg_codec_decode");
	check(decoded.ApplId == 0x0101 && decoded.Command == CAPI_ALERT &&
	      decoded.Subcommand == CAPI_REQ && decoded.Messagenumber == 0x0042,
	      "cmsg_codec_roundtrip_fields");
}

/* Case 2: command and information code rendering helpers. */
static void case_string_helpers(void)
{
	char *cmd = capi_cmd2str(CAPI_ALERT, CAPI_REQ);
	char *info = capi_info2str(CapiNoError);

	check(cmd != NULL && strstr(cmd, "ALERT") != NULL,
	      "cmd2str_renders_alert_request");
	check(info != NULL && strlen(info) > 0, "info2str_renders_no_error");
}

/* Case 3: dumping a _cmsg must mention the command it carries.  `cmsg->m` is a
 * pointer to the wire message, so the dump is taken from a decoded message. */
static void case_cmsg2str(void)
{
	_cmsg cmsg;
	_cmsg decoded;
	unsigned char msg[2048];
	char *text;

	capi_cmsg_header(&cmsg, 0x0101, CAPI_ALERT, CAPI_REQ, 0x0042, 0x00000000);
	capi_cmsg2message(&cmsg, msg);

	memset(&decoded, 0, sizeof(decoded));
	capi_message2cmsg(&decoded, msg);

	text = capi_cmsg2str(&decoded);
	check(text != NULL && strlen(text) > 0 && strstr(text, "ALERT") != NULL,
	      "cmsg2str_renders_message");
}

/* Case 4: driver name accessor round trip (pure library state, no driver used). */
static void case_ext_driver_roundtrip(void)
{
	char driver[] = "lib_capi_mod_fritzbox";

	capi20ext_set_driver(driver);
	check(capi20ext_get_driver() != NULL &&
	      strcmp(capi20ext_get_driver(), driver) == 0,
	      "ext_driver_set_get_roundtrip");
}

/* Case 5: host/port/tracelevel accessors round trip. */
static void case_ext_host_port_roundtrip(void)
{
	char host[] = "127.0.0.1";

	capi20ext_set_host(host);
	capi20ext_set_port(2662);
	capi20ext_set_tracelevel(3);

	check(capi20ext_get_host() != NULL &&
	      strcmp(capi20ext_get_host(), host) == 0, "ext_host_set_get_roundtrip");
	check(capi20ext_get_port() == 2662, "ext_port_set_get_roundtrip");
	check(capi20ext_get_tracelevel() == 3, "ext_tracelevel_set_get_roundtrip");
}

/* Case 6: without a CAPI driver the library reports the failure and stays usable */
static void case_without_driver(void)
{
	/* CAPI 2.0 returns at most CAPI_MANUFACTURER_LEN (64) bytes here; that
	   constant lives in capi_defs.h which upstream does not install. */
	unsigned char buf[64];
	unsigned rc;

	unsetenv("CAPI20_MODULE_DIR");
	rc = capi20_isinstalled();
	check(rc != CapiNoError, "isinstalled_reports_missing_driver");

	memset(buf, 0, sizeof(buf));
	check(capi20_get_version(0x01, buf) == NULL,
	      "get_version_returns_null_without_driver");
	check(capi20_get_manufacturer(0x01, buf) == NULL,
	      "get_manufacturer_returns_null_without_driver");

	/* The accessors still answer after a failed device probe. */
	check(capi20ext_get_tracelevel() == 3, "library_state_survives_probe");
}

int main(void)
{
	/* Unbuffered: the per case results must stay visible even if a later case
	   takes the process down. */
	setvbuf(stdout, NULL, _IONBF, 0);

	printf("libcapi20 adaptation tests (upstream test suite: none)\n");

	case_cmsg_codec_roundtrip();
	case_string_helpers();
	case_cmsg2str();
	case_ext_driver_roundtrip();
	case_ext_host_port_roundtrip();
	case_without_driver();

	printf("assertions: %d/%d passed\n", g_total - g_failed, g_total);
	return g_failed == 0 ? 0 : 1;
}
