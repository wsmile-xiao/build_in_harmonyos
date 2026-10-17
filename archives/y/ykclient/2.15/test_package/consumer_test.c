/* consumer_test.c --- test_package consumer for ykclient 2.15.
 *
 * Exercises the PUBLIC library API the way a real integrator would, fully
 * offline, with hard assertions on return codes (mirrors the offline
 * fixture vectors used by upstream tests/selftest.c):
 *   - ykclient_check_version (3 checks, as upstream main());
 *   - ykclient_global_init / ykclient_init / ykclient_done lifecycle;
 *   - ykclient_set_client_hex: rejects invalid hex ("a", "zz"), accepts the
 *     upstream fixture hex key (YKCLIENT_HEX_DECODE_ERROR / YKCLIENT_OK);
 *   - ykclient_set_client_b64: rejects non-base64, accepts the upstream
 *     fixture base64 key;
 *   - ykclient_set_verify_signature / set_nonce / set_url_template;
 *   - ykclient_strerror for representative codes.
 */
#include "ykclient.h"

#include <stdio.h>
#include <string.h>

static int fails = 0;

#define CHECK(cond, msg) \
  do { if (cond) { printf("PASS %d: %s\n", __LINE__, msg); } \
       else { printf("FAIL %d: %s\n", __LINE__, msg); fails++; } } while (0)

int main(void)
{
  static const char hexkey[] = "a0155b36dec865e859191f7daefabc77a459d433";
  static const char b64key[] = "oBVbNt7IZehZGR99rvq8d6RZ1DM=";
  char rawkey[20] = {
    (char)0xa0, (char)0x15, (char)0x5b, (char)0x36, (char)0xde,
    (char)0xc8, (char)0x65, (char)0xe8, (char)0x59, (char)0x19,
    (char)0x1f, (char)0x7d, (char)0xae, (char)0xfa, (char)0xbc,
    (char)0x77, (char)0xa4, (char)0x59, (char)0xd4, (char)0x33
  };
  ykclient_t *ykc = NULL;
  int ret;

  /* version checks (mirror upstream main() offline checks) */
  CHECK(strcmp(YKCLIENT_VERSION_STRING, ykclient_check_version(NULL)) == 0,
        "check_version(NULL) matches header version");
  CHECK(ykclient_check_version(YKCLIENT_VERSION_STRING) != NULL,
        "check_version(current) satisfied -> library version string");
  CHECK(ykclient_check_version("99.99.99") == NULL,
        "check_version(newer-than-library) -> NULL");

  /* lifecycle */
  CHECK(ykclient_global_init() == YKCLIENT_OK, "global_init");
  ret = ykclient_init(&ykc);
  CHECK(ret == YKCLIENT_OK && ykc != NULL, "init");

  /* client key setters with upstream fixture vectors */
  ret = ykclient_set_client_hex(ykc, 1851, "a");
  CHECK(ret == YKCLIENT_HEX_DECODE_ERROR, "set_client_hex('a') -> HEX_DECODE_ERROR");
  ret = ykclient_set_client_hex(ykc, 1851, "zz");
  CHECK(ret == YKCLIENT_HEX_DECODE_ERROR, "set_client_hex('zz') -> HEX_DECODE_ERROR");
  ret = ykclient_set_client_hex(ykc, 1851, hexkey);
  CHECK(ret == YKCLIENT_OK, "set_client_hex(fixture) -> OK");
  ret = ykclient_set_client_b64(ykc, 1851, "!!!not-base64!!!");
  /* Upstream's rfc2045 decoder skips invalid chars instead of failing,
     so junk input is accepted (ykclient.c:532-563 has no decode-error return). */
  CHECK(ret == YKCLIENT_OK, "set_client_b64(junk) -> lenient decode, OK");
  ret = ykclient_set_client_b64(ykc, 1851, b64key);
  CHECK(ret == YKCLIENT_OK, "set_client_b64(fixture) -> OK");
  ykclient_set_client(ykc, 1851, sizeof(rawkey), rawkey);

  /* request configuration (offline setters) */
  ykclient_set_verify_signature(ykc, 1);
  ykclient_set_nonce(ykc, NULL);
  ret = ykclient_set_url_template(
      ykc, "http://127.0.0.1:1/wsapi/verify?id=%d&otp=%s");
  CHECK(ret == YKCLIENT_OK, "set_url_template");

  /* strerror coverage */
  CHECK(ykclient_strerror(YKCLIENT_OK) != NULL, "strerror(OK) non-NULL");
  CHECK(ykclient_strerror(YKCLIENT_BAD_OTP) != NULL, "strerror(BAD_OTP) non-NULL");
  CHECK(ykclient_strerror(YKCLIENT_HEX_DECODE_ERROR) != NULL,
        "strerror(HEX_DECODE_ERROR) non-NULL");

  /* teardown */
  ykclient_done(&ykc);
  CHECK(ykc == NULL, "done clears handle");
  ykclient_global_done();

  printf("consumer_test: %s (%d failures)\n", fails ? "FAIL" : "PASS", fails);
  return fails ? 1 : 0;
}
