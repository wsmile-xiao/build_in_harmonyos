/*
 * Consumer + platform probe for the packaged qpid-proton (HarmonyOS PC).
 *
 * This program is the "test_package" of archives/q/qpid-proton/0.38.0: it
 * links against the *installed* package (find_package(Proton) -> the CMake
 * config that ships inside the package) and exercises the API surface that the
 * downstream consumer (openmama's qpid middleware bridge / qpidmsg payload
 * bridge) actually uses: the messenger API, pn_message/pn_data codecs and the
 * AMQP 1.0 wire format.
 *
 * Every check prints one "CHECK-OK: <group>/<name>" line.  The conanfile counts
 * those lines (machine evidence) and requires the process exit code to be 0,
 * so a stub binary that prints nothing can never pass.  Groups:
 *   platform - HarmonyOS/HMOS specific properties, including the regression
 *              check for the EPOLLONESHOT workaround in patches/0001
 *   consumer - real use of the packaged library API
 */

#define _GNU_SOURCE

#include <proton/codec.h>
#include <proton/message.h>
#include <proton/messenger.h>
#include <proton/proactor.h>
#include <proton/ssl.h>
#include <proton/types.h>
#include <proton/version.h>

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static int g_checks = 0;
static int g_failures = 0;

#define CHECK(name, cond)                                                      \
  do {                                                                         \
    ++g_checks;                                                                \
    if (cond) {                                                                \
      printf("CHECK-OK: %s\n", name);                                          \
    } else {                                                                   \
      ++g_failures;                                                            \
      printf("CHECK-FAIL: %s\n", name);                                        \
    }                                                                          \
    fflush(stdout);                                                            \
  } while (0)

/* ---------------------------------------------------------------- platform */

/* HarmonyOS PC is aarch64 with the LP64 data model. */
static int check_lp64(void) {
  return sizeof(void *) == 8 && sizeof(long) == 8 && sizeof(int) == 4 &&
         sizeof(long long) == 8;
}

static int check_little_endian(void) {
  uint32_t value = 0x01020304u;
  return ((const unsigned char *)&value)[0] == 0x04;
}

/* HarmonyOS user space is musl based: no glibc, and confstr() has no GNU libc
 * version to report (the poisoned buffer stays untouched).  musl defines
 * neither __musl__ nor __MUSL__, so this is a behavioural probe. */
static int check_musl_libc(void) {
#ifdef __GLIBC__
  return 0;
#else
  char buf[256];
  memset(buf, 0x7f, sizeof(buf));
  return confstr(_CS_GNU_LIBC_VERSION, buf, sizeof(buf)) == 0 &&
         buf[0] == (char)0x7f;
#endif
}

/* Wait for the next non-empty event batch and return its first event type.
 * Mirrors the upstream test harness (pn_proactor_wait() may hand out an empty
 * batch, PROTON-1964), bounded so a broken proactor fails instead of hanging. */
static pn_event_type_t wait_first_event(pn_proactor_t *proactor) {
  for (int attempt = 0; attempt < 100; ++attempt) {
    pn_event_batch_t *batch = pn_proactor_wait(proactor);
    if (!batch) continue;
    pn_event_t *event;
    pn_event_type_t first = PN_EVENT_NONE;
    while ((event = pn_event_batch_next(batch))) {
      if (first == PN_EVENT_NONE) first = pn_event_type(event);
    }
    pn_proactor_done(proactor, batch);
    if (first != PN_EVENT_NONE) return first;
  }
  return PN_EVENT_NONE;
}

/* ---------------------------------------------------------------- consumer */

static pn_message_t *make_message(void) {
  pn_message_t *message = pn_message();
  if (!message) return NULL;
  pn_message_set_address(message, "amqp://localhost/queue");
  pn_message_set_subject(message, "OHOS");
  pn_data_put_string(pn_message_body(message), pn_bytes(5, "hello"));
  return message;
}

int main(void) {
  /* ---- platform: data model and libc ---- */
  CHECK("platform/lp64", check_lp64());
  CHECK("platform/little-endian", check_little_endian());
  CHECK("platform/musl-libc", check_musl_libc());

  /* ---- platform: epoll proactor scheduling (patches/0001 regression) ----
   * HarmonyOS epoll ignores EPOLLONESHOT.  Before the patch the proactor's
   * ready-list eventfd stayed readable forever, so pn_proactor_get() below
   * never returned and pn_proactor_wait() span instead of blocking. */
  {
    pn_proactor_t *proactor = pn_proactor();
    int interrupt_ok = 0, timeout_ok = 0;
    if (proactor) {
      pn_proactor_interrupt(proactor);
      interrupt_ok = wait_first_event(proactor) == PN_PROACTOR_INTERRUPT;
      pn_proactor_set_timeout(proactor, 0);
      timeout_ok = wait_first_event(proactor) == PN_PROACTOR_TIMEOUT;
    }
    CHECK("platform/proactor-interrupt-event", interrupt_ok);
    CHECK("platform/proactor-timeout-inactive",
          timeout_ok && wait_first_event(proactor) == PN_PROACTOR_INACTIVE);
    if (proactor) {
      /* Arm and cancel a long timeout: no timeout event may be reported. */
      pn_proactor_set_timeout(proactor, 10000000);
      pn_proactor_cancel_timeout(proactor);
      int cancelled_ok =
          wait_first_event(proactor) == PN_PROACTOR_INACTIVE;
      int idle_ok = pn_proactor_get(proactor) == NULL;
      CHECK("platform/proactor-idle-get-null", cancelled_ok && idle_ok);
      pn_proactor_free(proactor);
    } else {
      CHECK("platform/proactor-idle-get-null", 0);
    }
  }

  /* ---- consumer: version metadata (libqpid-proton 0.38.0) ---- */
  CHECK("consumer/version-macro",
        PN_VERSION_MAJOR == 0 && PN_VERSION_MINOR == 38 &&
            PN_VERSION_POINT == 0);

  /* ---- consumer: AMQP 1.0 wire format conformance ----
   * A message with only a body must encode to three described sections:
   *   00 53 70 45                      header      (empty list)
   *   00 53 73 45                      properties  (empty list)
   *   00 53 77 a1 05 68 65 6c 6c 6f    amqp-value  (str8 "hello")
   * 0x53/0x73/0x70/0x77 are the AMQP 1.0 smallulong descriptor encodings of
   * amqp:header/amqp:properties/amqp:amqp-value and 0x45/0xa1 the list0/str8
   * type codes, so this pins the produced bytes to the wire specification. */
  {
    static const unsigned char expected[] = {
        0x00, 0x53, 0x70, 0x45,                    /* header (empty)   */
        0x00, 0x53, 0x73, 0x45,                    /* properties (empty)*/
        0x00, 0x53, 0x77, 0xa1, 0x05,              /* amqp-value, str8 */
        0x68, 0x65, 0x6c, 0x6c, 0x6f};             /* "hello"          */
    pn_message_t *message = pn_message();
    pn_data_put_string(pn_message_body(message), pn_bytes(5, "hello"));
    char buffer[256];
    size_t size = sizeof(buffer);
    int rc = pn_message_encode(message, buffer, &size);
    int ok = rc == 0 && size == sizeof(expected) &&
             memcmp(buffer, expected, sizeof(expected)) == 0;
    if (!ok) {
      printf("  wire bytes (%zu):", size);
      for (size_t i = 0; i < size && i < 32; ++i)
        printf(" %02x", (unsigned char)buffer[i]);
      printf("\n");
    }
    CHECK("consumer/amqp-wire-conformance", ok);
    pn_message_free(message);
  }

  /* ---- consumer: message encode/decode round trip ---- */
  {
    pn_message_t *message = make_message();
    char buffer[512];
    size_t size = sizeof(buffer);
    int ok = message != NULL &&
             pn_message_encode(message, buffer, &size) == 0;
    pn_message_t *decoded = pn_message();
    ok = ok && decoded != NULL &&
         pn_message_decode(decoded, buffer, size) == 0;
    if (ok) {
      pn_data_t *body = pn_message_body(decoded);
      pn_data_next(body);
      pn_bytes_t text = pn_data_get_string(body);
      ok = strcmp(pn_message_get_address(decoded), "amqp://localhost/queue") ==
               0 &&
           strcmp(pn_message_get_subject(decoded), "OHOS") == 0 &&
           text.size == 5 && memcmp(text.start, "hello", 5) == 0;
    }
    CHECK("consumer/message-roundtrip", ok);
    pn_message_free(decoded);
    if (message) pn_message_free(message);
  }

  /* ---- consumer: pn_data map codec (the shape openmama's codec uses) ----
   * Builds a map with the atom types openmama's mamaqpidimpl codec writes
   * (string/ubyte/binary), round-trips it through the AMQP 1.0 encoder and
   * reads the entries back with pn_data_lookup()/pn_data_get_*(), exactly the
   * navigation pattern of mama/c_cpp/src/c/bridge/qpid/codec.c. */
  {
    pn_data_t *source = pn_data(16);
    pn_data_put_map(source);
    pn_data_enter(source);
    pn_data_put_string(source, pn_bytes(4, "key1"));
    pn_data_put_string(source, pn_bytes(6, "value1"));
    pn_data_put_string(source, pn_bytes(4, "key2"));
    pn_data_put_ubyte(source, 7);
    pn_data_put_string(source, pn_bytes(4, "key3"));
    pn_data_put_binary(source, pn_bytes(3, "\x01\x02\x03"));
    pn_data_exit(source);
    char buffer[512];
    ssize_t encoded = pn_data_encode(source, buffer, sizeof(buffer));
    pn_data_t *decoded = pn_data(16);
    ssize_t consumed = pn_data_decode(
        decoded, buffer, encoded > 0 ? (size_t)encoded : 0);
    int ok = encoded > 0 && consumed == encoded &&
             pn_data_type(decoded) == PN_MAP && pn_data_get_map(decoded) == 6;
    if (ok) {
      /* openmama enters the map and then walks the entries with
       * pn_data_lookup(), which advances from the current position. */
      pn_data_enter(decoded);
      ok = pn_data_lookup(decoded, "key1") &&
           pn_data_type(decoded) == PN_STRING &&
           pn_data_get_string(decoded).size == 6 &&
           memcmp(pn_data_get_string(decoded).start, "value1", 6) == 0;
      ok = ok && pn_data_lookup(decoded, "key2") &&
           pn_data_get_ubyte(decoded) == 7;
      ok = ok && pn_data_lookup(decoded, "key3") &&
           pn_data_get_binary(decoded).size == 3 &&
           memcmp(pn_data_get_binary(decoded).start, "\x01\x02\x03", 3) == 0;
    }
    CHECK("consumer/data-map-roundtrip", ok);
    pn_data_free(decoded);
    pn_data_free(source);
  }

  /* ---- consumer: TLS availability (OpenSSL built in, not the stub) ---- */
  {
    pn_ssl_domain_t *domain = pn_ssl_domain(PN_SSL_MODE_CLIENT);
    int ok = pn_ssl_present() && domain != NULL;
    if (domain) pn_ssl_domain_free(domain);
    CHECK("consumer/tls-available", ok);
  }

  /* ---- consumer: messenger API lifecycle (openmama's qpid bridge path) ---
   * pn_messenger() carries a deprecated marker upstream, but the messenger API
   * is exactly what the downstream consumer (openmama's mamaqpidimpl bridge)
   * drives through this library, so it is exercised on purpose. */
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
  {
    pn_messenger_t *messenger = pn_messenger("ohos-proton-consumer");
    int ok = messenger != NULL &&
             strcmp(pn_messenger_name(messenger), "ohos-proton-consumer") == 0 &&
             pn_messenger_start(messenger) == 0 &&
             pn_messenger_stop(messenger) == 0;
    if (messenger) pn_messenger_free(messenger);
    CHECK("consumer/messenger-lifecycle", ok);
  }
  {
    pn_messenger_t *messenger = pn_messenger("ohos-proton-consumer-sub");
    int ok = messenger != NULL && pn_messenger_set_timeout(messenger, 1) == 0 &&
             pn_messenger_subscribe(messenger, "amqp://localhost/queue") != NULL &&
             pn_messenger_start(messenger) == 0 &&
             pn_messenger_stop(messenger) == 0;
    if (messenger) pn_messenger_free(messenger);
    CHECK("consumer/messenger-subscribe", ok);
  }
#pragma clang diagnostic pop

  printf("consumer checks: %d run, %d failed\n", g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
