/* Consumer-side verification of rhonabwy/1.1.13 on HarmonyOS PC.
 *
 * Uses nothing but the installed package: find_package(Rhonabwy) ->
 * Rhonabwy::Rhonabwy plus the C standard library. It exercises the public JOSE
 * API end to end - symmetric JWK import/validation/export, JWS HS256 signing,
 * compact serialisation, parsing, signature verification and rejection of a
 * tampered token - so a broken package (missing symbol, wrong header,
 * unloadable shared object) fails the test instead of returning 0. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <rhonabwy.h>

static int failures = 0;
static int assertions = 0;

#define CHECK_INT(expr, expected, msg)                                        \
  do {                                                                        \
    int _got = (int)(expr);                                                   \
    assertions++;                                                             \
    if (_got != (int)(expected)) {                                            \
      failures++;                                                             \
      fprintf(stderr, "not ok - %s: got %d, expected %d (line %d)\n",          \
              (msg), _got, (int)(expected), __LINE__);                        \
    } else {                                                                  \
      printf("ok - %s\n", (msg));                                             \
    }                                                                         \
  } while (0)

#define CHECK_TRUE(expr, msg)                                                 \
  do {                                                                        \
    assertions++;                                                             \
    if (!(expr)) {                                                            \
      failures++;                                                             \
      fprintf(stderr, "not ok - %s (line %d)\n", (msg), __LINE__);             \
    } else {                                                                  \
      printf("ok - %s\n", (msg));                                             \
    }                                                                         \
  } while (0)

static const char JWK_OCT[] =
  "{\"kty\":\"oct\",\"alg\":\"HS256\",\"k\":\"c2VjcmV0\",\"kid\":\"1\"}";

static const char PAYLOAD[] =
  "The true sign of intelligence is not knowledge but imagination.";

int main(void) {
  jwk_t *jwk = NULL;
  jws_t *jws = NULL;
  jws_t *parsed = NULL;
  jws_t *tampered_jws = NULL;
  char *token = NULL;
  char *exported = NULL;
  char *tampered = NULL;
  size_t last = 0;

  CHECK_INT(r_jwk_init(&jwk), RHN_OK, "r_jwk_init");
  CHECK_INT(r_jwk_import_from_json_str(jwk, JWK_OCT), RHN_OK,
            "r_jwk_import_from_json_str(symmetric)");
  CHECK_INT(r_jwk_is_valid(jwk), RHN_OK, "r_jwk_is_valid");

  exported = r_jwk_export_to_json_str(jwk, 0);
  CHECK_TRUE(exported != NULL, "r_jwk_export_to_json_str");
  CHECK_TRUE(exported != NULL && strstr(exported, "\"oct\"") != NULL,
             "exported JWK keeps kty=oct");
  free(exported);
  exported = NULL;
  if (failures) {
    goto done;
  }

  /* ── JWS HS256 signing ── */
  CHECK_INT(r_jws_init(&jws), RHN_OK, "r_jws_init");
  CHECK_INT(r_jws_set_payload(jws, (const unsigned char *)PAYLOAD,
                              strlen(PAYLOAD)), RHN_OK, "r_jws_set_payload");
  CHECK_INT(r_jws_set_alg(jws, R_JWA_ALG_HS256), RHN_OK, "r_jws_set_alg(HS256)");
  CHECK_INT(r_jws_add_keys(jws, jwk, NULL), RHN_OK, "r_jws_add_keys");
  token = r_jws_serialize(jws, NULL, 0);
  CHECK_TRUE(token != NULL, "r_jws_serialize");
  if (token == NULL) {
    goto done;
  }
  /* A compact JWS is header.payload.signature. */
  CHECK_TRUE(strchr(token, '.') != NULL, "compact JWS contains a dot separator");
  CHECK_TRUE(strlen(token) > strlen(PAYLOAD),
             "compact JWS carries a signature");

  /* ── parse + verify the produced token ── */
  CHECK_INT(r_jws_init(&parsed), RHN_OK, "r_jws_init(parse)");
  CHECK_INT(r_jws_parse(parsed, token, 0), RHN_OK, "r_jws_parse");
  CHECK_INT(r_jws_verify_signature(parsed, jwk, 0), RHN_OK,
            "r_jws_verify_signature(valid token)");

  /* ── a tampered signature must be rejected ── */
  tampered = strdup(token);
  CHECK_TRUE(tampered != NULL, "strdup(token)");
  if (tampered != NULL) {
    last = strlen(tampered) - 1;
    tampered[last] = (tampered[last] == 'A') ? 'B' : 'A';
    CHECK_INT(r_jws_init(&tampered_jws), RHN_OK, "r_jws_init(tampered)");
    CHECK_INT(r_jws_parse(tampered_jws, tampered, 0), RHN_OK,
              "r_jws_parse(tampered)");
    CHECK_TRUE(r_jws_verify_signature(tampered_jws, jwk, 0) != RHN_OK,
               "r_jws_verify_signature(tampered token) is rejected");
  }

done:
  free(tampered);
  free(token);
  if (tampered_jws != NULL) {
    r_jws_free(tampered_jws);
  }
  if (parsed != NULL) {
    r_jws_free(parsed);
  }
  if (jws != NULL) {
    r_jws_free(jws);
  }
  if (jwk != NULL) {
    r_jwk_free(jwk);
  }

  printf("# %d assertions, %d failures\n", assertions, failures);
  return failures == 0 ? 0 : 1;
}
