/* Consumer-perspective smoke test for belle-sip 5.3.105 on HarmonyOS PC.
 *
 * Plays the role of a third-party application that installs the Conan package
 * and uses only the public C API: SIP URI parsing and SIP message parsing with
 * typed header access.
 */
#include <belle-sip/belle-sip.h>

#include <stdio.h>
#include <string.h>

static int g_checks = 0;
static int g_failures = 0;

static void check(int ok, const char *what) {
  g_checks++;
  if (!ok) {
    g_failures++;
    printf("CHECK FAILED: %s\n", what);
  }
}

int main(void) {
  /* ── SIP URI parsing ── */
  belle_sip_uri_t *uri = belle_sip_uri_parse("sip:toto@1titi.com:5060;transport=tcp");
  check(uri != NULL, "SIP URI parses");
  if (uri != NULL) {
    check(strcmp(belle_sip_uri_get_user(uri), "toto") == 0, "URI user is parsed");
    check(strcmp(belle_sip_uri_get_host(uri), "1titi.com") == 0, "URI host is parsed");
    check(belle_sip_uri_get_port(uri) == 5060, "URI port is parsed");
    check(belle_sip_uri_get_transport_param(uri) != NULL &&
              strcmp(belle_sip_uri_get_transport_param(uri), "tcp") == 0,
          "URI transport parameter is parsed");
    check(belle_sip_uri_to_string(uri) != NULL, "URI can be serialised back");
    belle_sip_object_unref(uri);
  }

  /* ── SIP message parsing with typed header access ── */
  const char *raw =
      "INVITE sip:bob@example.com SIP/2.0\r\n"
      "Via: SIP/2.0/UDP 127.0.0.1:5060;branch=z9hG4bK.1\r\n"
      "From: \"Alice\" <sip:alice@example.com>;tag=abc123\r\n"
      "To: <sip:bob@example.com>\r\n"
      "Call-ID: 1@127.0.0.1\r\n"
      "CSeq: 1 INVITE\r\n"
      "Content-Length: 0\r\n\r\n";
  belle_sip_message_t *message = belle_sip_message_parse(raw);
  check(message != NULL, "SIP message parses");
  if (message != NULL) {
    belle_sip_request_t *request = BELLE_SIP_REQUEST(message);
    check(request != NULL, "message can be cast to a SIP request");
    if (request != NULL) {
      check(strcmp(belle_sip_request_get_method(request), "INVITE") == 0,
            "request method is parsed");
    }
    belle_sip_header_from_t *from =
        belle_sip_message_get_header_by_type(message, belle_sip_header_from_t);
    check(from != NULL, "From header is accessible by type");
    if (from != NULL) {
      check(strcmp(belle_sip_header_from_get_tag(from), "abc123") == 0,
            "From header tag is parsed");
    }
    char *serialised = belle_sip_object_to_string(BELLE_SIP_OBJECT(message));
    check(serialised != NULL, "message can be serialised back");
    belle_sip_free(serialised);
    belle_sip_object_unref(message);
  }

  printf("BELLESIP_CONSUMER_CHECKS=%d FAILURES=%d\n", g_checks, g_failures);
  if (g_failures != 0) {
    printf("BELLESIP_CONSUMER_FAILED\n");
    return 1;
  }
  printf("BELLESIP_CONSUMER_OK\n");
  return 0;
}
