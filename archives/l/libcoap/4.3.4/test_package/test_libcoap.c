/* Consumer test for libcoap 4.3.4.
 * Exercises the public CoAP PDU API: init -> inspect -> add option/data ->
 * read back -> free. Exit code 0 only when all checks pass. */

#include <stdio.h>
#include <string.h>

#include <coap3/coap.h>

static int g_checks = 0;
static int g_fails = 0;

static void check(int ok, const char* what, int line) {
    ++g_checks;
    if (!ok) {
        fprintf(stderr, "FAIL(line %d): %s\n", line, what);
        ++g_fails;
    }
}

#define CHECK(expr) check((expr), #expr, __LINE__)

int main(void)
{
   coap_startup();

   coap_pdu_t *pdu = coap_pdu_init(COAP_MESSAGE_CON, COAP_REQUEST_CODE_GET,
                                   0x1234, 1024);
   CHECK(pdu != NULL);

   if (pdu)
   {
      CHECK(coap_pdu_get_type(pdu) == COAP_MESSAGE_CON);
      CHECK(coap_pdu_get_code(pdu) == COAP_REQUEST_CODE_GET);
      CHECK(coap_pdu_get_mid(pdu) == 0x1234);

      size_t added = coap_add_option(pdu, COAP_OPTION_URI_PATH, 4,
                                     (const uint8_t *)"time");
      /* 返回值为选项总长（含 option 头字节），失败返回 0 */
      CHECK(added != 0);

      static const char body[] = "hello-coap";
      CHECK(coap_add_data(pdu, sizeof(body) - 1, (const uint8_t *)body) != 0);

      size_t len = 0;
      const uint8_t *data = NULL;
      CHECK(coap_get_data(pdu, &len, &data) != 0);
      CHECK(len == sizeof(body) - 1);
      CHECK(data != NULL && memcmp(data, body, len) == 0);

      coap_delete_pdu(pdu);
   }

   coap_cleanup();

   if (g_fails == 0)
   {
      printf("libcoap consumer test: %d/%d checks passed\n", g_checks, g_checks);
      return 0;
   }
   fprintf(stderr, "libcoap consumer test: %d/%d check(s) failed\n", g_fails, g_checks);
   return 1;
}
