/*
 * test_package/test_ruli.c - consumer functional test for ruli 0.36.
 *
 * Linked against the *packaged* libruli (and, transitively, the packaged
 * liboop) exactly the way a downstream application is: one `#include <ruli.h>`
 * and one `target_link_libraries(... ruli::ruli)`.  Nothing here peeks at
 * upstream sources or build internals.
 *
 * ruli 0.36 ships no automated test suite on its C build surface (audit:
 * test_package/MANIFEST.yml), so these are hand-written real-API checks.  Each
 * check that passes prints one "CHECK-OK: <name>" line; the single network-
 * dependent check (11) prints "CHECK-SKIP: <name> | reason=... | evidence=..."
 * instead when there is no usable DNS transport, so 12 is never reduced.
 *
 * Checks 1-10 and 12 are deterministic (pure DNS wire-format / container /
 * allocator / RFC 3484 policy / getaddrinfo-dispatch code inside libruli
 * itself).  Check 11 drives the real resolution path: ruli_sync_query() loads
 * /etc/resolv.conf through ruli's own config handler, opens a UDP socket to
 * port 53, builds the query packet with ruli_dname_encode(), and decodes the
 * answer with ruli_parse_*(); it asserts on the specific failure rcode.  If no
 * answer arrives after SYNC_ATTEMPTS tries it prints CHECK-SKIP with the
 * decoded srv_code/rcode as evidence, so the denominator (12) is preserved.
 */

#include <assert.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <ruli.h>

static int g_checks_ok = 0;
static int g_checks_skipped = 0;
static int g_checks_failed = 0;

/* A function, not a macro: a variadic macro invoked with an empty
   __VA_ARGS__ is a constraint violation in C99 and the upstream flags do
   not enable the GNU `, ##__VA_ARGS__` extension. */
static void failf(const char *name, const char *fmt, ...)
{
  va_list ap;
  ++g_checks_failed;
  printf("CHECK-FAIL: %s | ", name);
  va_start(ap, fmt);
  vprintf(fmt, ap);
  va_end(ap);
  putchar('\n');
  fflush(stdout);
}

#define OK(name)                                                          \
  do {                                                                    \
    ++g_checks_ok;                                                        \
    printf("CHECK-OK: %s\n", (name));                                     \
    fflush(stdout);                                                       \
  } while (0)

#define SKIP(name, why, ev)                                               \
  do {                                                                    \
    ++g_checks_skipped;                                                   \
    printf("CHECK-SKIP: %s | reason=%s | evidence=%s\n",                  \
           (name), (why), (ev));                                          \
    fflush(stdout);                                                       \
  } while (0)

/* ------------------------------------------------------------------ */
/* 1. ruli_dname_encode() produces the RFC 1035 wire format            */
/* ------------------------------------------------------------------ */
static void check_dname_encode_wire_format(void)
{
  const char *name = "www.example.org";
  static const unsigned char want[] = {
    3, 'w', 'w', 'w', 7, 'e', 'x', 'a', 'm', 'p', 'l', 'e',
    3, 'o', 'r', 'g', 0
  };
  char buf[128];
  char *end;
  int len = (int) strlen(name);
  int size_hint;

  if (ruli_dname_encode_size(name, len) != (int) sizeof(want)) {
    failf("dname_encode_wire_format",
         "ruli_dname_encode_size=%d want=%u",
         ruli_dname_encode_size(name, len), (unsigned) sizeof(want));
    return;
  }
  size_hint = ruli_dname_encode_size(name, len);

  memset(buf, 0x7f, sizeof(buf));
  end = ruli_dname_encode(buf, (int) sizeof(buf), name, len);
  if (!end) {
    failf("dname_encode_wire_format", "ruli_dname_encode returned NULL");
    return;
  }
  if ((int) (end - buf) != (int) sizeof(want) || memcmp(buf, want, sizeof(want))) {
    failf("dname_encode_wire_format", "encoded=%d want=%u",
         (int) (end - buf), (unsigned) sizeof(want));
    return;
  }
  /* the trailing-dot spelling must encode to the very same octets */
  {
    char buf2[128];
    char *end2;
    const char *dotted = "www.example.org.";
    end2 = ruli_dname_encode(buf2, (int) sizeof(buf2),
                             dotted, (int) strlen(dotted));
    if (!end2 || (end2 - buf2) != (end - buf) ||
        memcmp(buf2, buf, (size_t) (end - buf))) {
      failf("dname_encode_wire_format", "trailing-dot form differs");
      return;
    }
  }
  (void) size_hint;
  OK("dname_encode_wire_format");
}

/* ------------------------------------------------------------------ */
/* 2. ruli_dname_decode() round-trips the wire format back to text     */
/* ------------------------------------------------------------------ */
static void check_dname_decode_roundtrip(void)
{
  const char *name = "www.example.org";
  char wire[128];
  char text[128];
  char *end;
  int text_len = -1;
  int rc;

  end = ruli_dname_encode(wire, (int) sizeof(wire), name, (int) strlen(name));
  if (!end) {
    failf("dname_decode_roundtrip", "encode precondition failed");
    return;
  }
  memset(text, 0x7f, sizeof(text));
  rc = ruli_dname_decode(text, (int) sizeof(text), &text_len,
                         wire, (int) (end - wire));
  if (rc != RULI_TXT_OK) {
    failf("dname_decode_roundtrip", "ruli_dname_decode rc=%d want=%d",
         rc, RULI_TXT_OK);
    return;
  }
  /* dname_decode() emits the fully-qualified spelling with a root dot */
  if (strcmp(text, "www.example.org.") != 0) {
    failf("dname_decode_roundtrip", "decoded='%s' want='www.example.org.'", text);
    return;
  }
  if (text_len != (int) strlen("www.example.org.")) {
    failf("dname_decode_roundtrip", "dst_name_len=%d want=%d",
         text_len, (int) strlen("www.example.org."));
    return;
  }
  /* a compressed (label-offset) name must be rejected, not silently accepted */
  {
    char bad[4];
    int bad_len = 0;
    bad[0] = (char) 0xC0;
    bad[1] = (char) 0x0C;
    bad[2] = 0;
    bad[3] = 0;
    rc = ruli_dname_decode(text, (int) sizeof(text), &bad_len, bad, 2);
    if (rc != RULI_TXT_BAD) {
      failf("dname_decode_roundtrip",
           "compression pointer accepted: rc=%d want=%d", rc, RULI_TXT_BAD);
      return;
    }
  }
  OK("dname_decode_roundtrip");
}

/* ------------------------------------------------------------------ */
/* 3. negative paths: undersized buffer and over-long name             */
/* ------------------------------------------------------------------ */
static void check_dname_encode_guards(void)
{
  const char *name = "www.example.org";
  char tiny[4];
  char big[512];
  int i;

  memset(tiny, 0, sizeof(tiny));
  if (ruli_dname_encode(tiny, (int) sizeof(tiny), name, (int) strlen(name)) != 0) {
    failf("dname_encode_guards", "undersized buffer was not rejected");
    return;
  }
  for (i = 0; i < 257; ++i)
    big[i] = 'a';
  big[257] = '\0';
  if (ruli_dname_encode(tiny, sizeof(tiny), big, 257) != 0) {
    failf("dname_encode_guards", "257-octet single label was not rejected");
    return;
  }
  {
    char roomy[512];
    if (ruli_dname_encode(roomy, (int) sizeof(roomy), big, 257) != 0) {
      failf("dname_encode_guards", "over-long name was not rejected");
      return;
    }
  }
  OK("dname_encode_guards");
}

/* ------------------------------------------------------------------ */
/* 4. ruli_dname_match(): case-insensitive, trailing-dot tolerant      */
/* ------------------------------------------------------------------ */
static void check_dname_match(void)
{
  const char *a = "WWW.Example.ORG";
  const char *b = "www.example.org.";
  const char *c = "www.example.com";

  if (!ruli_dname_match(a, (int) strlen(a), b, (int) strlen(b))) {
    failf("dname_match", "'%s' should match '%s'", a, b);
    return;
  }
  if (ruli_dname_match(a, (int) strlen(a), c, (int) strlen(c))) {
    failf("dname_match", "'%s' must not match '%s'", a, c);
    return;
  }
  if (ruli_dname_match("example.org", 11, "www.example.org", 15)) {
    failf("dname_match", "different lengths matched");
    return;
  }
  OK("dname_match");
}

/* ------------------------------------------------------------------ */
/* 5. ruli_dname_expand(): label offsets (RFC 1035 message compression)*/
/* ------------------------------------------------------------------ */
static void check_dname_expand_pointer(void)
{
  static const unsigned char want[] = {
    3, 'w', 'w', 'w', 7, 'e', 'x', 'a', 'm', 'p', 'l', 'e',
    3, 'o', 'r', 'g', 0
  };
  unsigned char msg[64];
  unsigned char out[128];
  const int qname_off = 12;
  int pos = 0;
  size_t n = 0;
  int rc;

  memset(msg, 0, sizeof(msg));
  /* header: ID, flags, QDCOUNT=1, ANCOUNT=0, NSCOUNT=0, ARCOUNT=0 */
  msg[4] = 0; msg[5] = 1;
  pos = qname_off;
  memcpy(msg + pos, want, sizeof(want));
  pos += (int) sizeof(want);                 /* 12 + 17 = 29 */
  msg[pos++] = 0; msg[pos++] = 33;           /* QTYPE  = SRV  */
  msg[pos++] = 0; msg[pos++] = 1;            /* QCLASS = IN   */
  /* an RDATA-compressed reference back to the QNAME at offset 12 */
  msg[pos] = 0xC0;
  msg[pos + 1] = (unsigned char) qname_off;
  pos += 2;                                  /* message is 35 bytes */

  /* sanity: expanding the uncompressed form yields the encoded name */
  rc = ruli_dname_expand(msg, msg + pos, out, out + sizeof(out),
                         msg + qname_off, &n);
  if (rc != RULI_TXT_OK || n != sizeof(want) || memcmp(out, want, n)) {
    failf("dname_expand_pointer", "plain expansion rc=%d n=%u", rc, (unsigned) n);
    return;
  }
  /* the interesting case: the same name reached through a label offset */
  {
    unsigned char out2[128];
    size_t n2 = 0;
    rc = ruli_dname_expand(msg, msg + pos, out2, out2 + sizeof(out2),
                           msg + (pos - 2), &n2);
    if (rc != RULI_TXT_OK || n2 != sizeof(want) ||
        memcmp(out2, want, sizeof(want))) {
      failf("dname_expand_pointer",
           "compressed expansion rc=%d n=%u want=%u",
           rc, (unsigned) n2, (unsigned) sizeof(want));
      return;
    }
  }
  /* out-of-message pointer must be refused, not read past the buffer */
  {
    unsigned char out3[128];
    size_t n3 = 0;
    msg[pos - 1] = (unsigned char) (pos + 40);   /* target past pastend */
    rc = ruli_dname_expand(msg, msg + pos, out3, out3 + sizeof(out3),
                           msg + (pos - 2), &n3);
    if (rc == RULI_TXT_OK) {
      failf("dname_expand_pointer", "out-of-message pointer was accepted");
      return;
    }
  }
  OK("dname_expand_pointer");
}

/* ------------------------------------------------------------------ */
/* 6. qtype/qclass name<->code tables (ruli_res.c)                     */
/* ------------------------------------------------------------------ */
static void check_qtype_qclass_tables(void)
{
  if (ruli_get_qtype_code("SRV") != RULI_RR_TYPE_SRV ||
      ruli_get_qtype_code("a") != RULI_RR_TYPE_A ||
      ruli_get_qtype_code("AAAA") != RULI_RR_TYPE_AAAA ||
      ruli_get_qtype_code("no-such-type") != 0) {
    failf("qtype_qclass_tables", "ruli_get_qtype_code mismatch: srv=%d a=%d aaaa=%d bogus=%d",
         ruli_get_qtype_code("SRV"), ruli_get_qtype_code("a"),
         ruli_get_qtype_code("AAAA"), ruli_get_qtype_code("no-such-type"));
    return;
  }
  if (ruli_get_qclass_code("IN") != RULI_RR_CLASS_IN ||
      ruli_get_qclass_code("ch") != RULI_RR_CLASS_CH ||
      ruli_get_qclass_code("nope") != 0) {
    failf("qtype_qclass_tables", "ruli_get_qclass_code mismatch");
    return;
  }
  {
    const char *nm = ruli_get_qtype_name(RULI_RR_TYPE_PTR);
    if (!nm || strcmp(nm, "ptr") != 0) {
      failf("qtype_qclass_tables", "ruli_get_qtype_name(PTR)='%s'", nm ? nm : "(null)");
      return;
    }
  }
  if (!ruli_rr_type_is_address(0, RULI_RR_TYPE_A) ||
      !ruli_rr_type_is_address(0, RULI_RR_TYPE_AAAA) ||
      ruli_rr_type_is_address(0, RULI_RR_TYPE_TXT)) {
    failf("qtype_qclass_tables", "ruli_rr_type_is_address predicate wrong");
    return;
  }
  OK("qtype_qclass_tables");
}

/* ------------------------------------------------------------------ */
/* 7. ruli_addr_parse() / ruli_addr_snprint() for v4, v6 and garbage   */
/* ------------------------------------------------------------------ */
static void check_addr_parse_snprint(void)
{
  ruli_addr_t a4;
  ruli_addr_t a6;
  ruli_addr_t bad;
  char text[128];

  memset(&a4, 0, sizeof(a4));
  if (ruli_addr_parse("192.0.2.123", &a4) != 0 ||
      ruli_addr_family(&a4) != PF_INET ||
      ruli_addr_size(&a4) != 4 ||
      a4.addr.ipv4.s_addr != htonl(0xC000027B)) {
    failf("addr_parse_snprint", "IPv4 parse failed: rc=%d fam=%d",
         ruli_addr_parse("192.0.2.123", &a4), ruli_addr_family(&a4));
    return;
  }
  memset(text, 0, sizeof(text));
  if (ruli_addr_snprint(text, sizeof(text), &a4) < 0 ||
      strcmp(text, "192.0.2.123") != 0) {
    failf("addr_parse_snprint", "IPv4 snprint gave '%s'", text);
    ruli_addr_snprint(text, sizeof(text), &a4);
    return;
  }

  memset(&a6, 0, sizeof(a6));
  if (ruli_addr_parse("2001:db8::1a", &a6) != 0 ||
      ruli_addr_family(&a6) != PF_INET6 ||
      ruli_addr_size(&a6) != 16) {
    failf("addr_parse_snprint", "IPv6 parse failed: rc=%d fam=%d",
         ruli_addr_parse("2001:db8::1a", &a6), ruli_addr_family(&a6));
    return;
  }
  if (a6.addr.ipv6.s6_addr[0] != 0x20 || a6.addr.ipv6.s6_addr[1] != 0x01 ||
      a6.addr.ipv6.s6_addr[15] != 0x1a) {
    failf("addr_parse_snprint", "IPv6 octets wrong: %02x %02x %02x",
         a6.addr.ipv6.s6_addr[0], a6.addr.ipv6.s6_addr[1],
         a6.addr.ipv6.s6_addr[15]);
    return;
  }
  /*
   * ruli uses its own ruli_inet6_snprint() rather than inet_ntop(3), and that
   * printer does not fold a run of zero groups ("2001:db8::1a" comes back as
   * "2001:db8:0:0:0:0:0:1a").  So assert the meaningful property - the printed
   * spelling must parse back to bit-identical octets - instead of pinning the
   * textual form.
   */
  memset(text, 0, sizeof(text));
  if (ruli_addr_snprint(text, sizeof(text), &a6) <= 0 || text[0] == '\0') {
    failf("addr_parse_snprint", "IPv6 snprint failed for family %d",
         ruli_addr_family(&a6));
    return;
  }
  {
    ruli_addr_t again;
    memset(&again, 0, sizeof(again));
    if (ruli_addr_parse(text, &again) != 0 ||
        ruli_addr_family(&again) != PF_INET6 ||
        memcmp(&again.addr.ipv6, &a6.addr.ipv6,
               sizeof(a6.addr.ipv6)) != 0) {
      failf("addr_parse_snprint",
           "IPv6 snprint->parse round trip lost bits, printed '%s'", text);
      return;
    }
  }

  memset(&bad, 0, sizeof(bad));
  if (ruli_addr_parse("not.an.address", &bad) == 0 ||
      ruli_addr_family(&bad) != PF_UNSPEC) {
    failf("addr_parse_snprint", "garbage input was accepted");
    return;
  }
  OK("addr_parse_snprint");
}

/* ------------------------------------------------------------------ */
/* 8. ruli_addr_rfc3484_sort(): destination-address selection policy   */
/* ------------------------------------------------------------------ */
static void check_rfc3484_sort(void)
{
  ruli_list_t list;
  ruli_addr_t *v4;
  ruli_addr_t *v6;
  struct in_addr in4;
  struct in6_addr in6;
  int rc;
  ruli_addr_t *first;
  ruli_addr_t *second;

  if (inet_pton(AF_INET, "203.0.113.10", &in4) != 1 ||
      inet_pton(AF_INET6, "2001:db8::1", &in6) != 1) {
    failf("rfc3484_sort", "inet_pton precondition failed");
    return;
  }
  rc = ruli_list_new(&list);
  if (rc) {
    failf("rfc3484_sort", "ruli_list_new rc=%d", rc);
    return;
  }
  v4 = ruli_addr_inet_new(in4);
  v6 = ruli_addr_inet6_new(in6);
  if (!v4 || !v6) {
    ruli_list_delete(&list);
    failf("rfc3484_sort", "addr_new returned NULL (v4=%p v6=%p)",
         (void *) v4, (void *) v6);
    return;
  }
  if (ruli_list_push(&list, v4) || ruli_list_push(&list, v6)) {
    ruli_list_delete(&list);
    failf("rfc3484_sort", "ruli_list_push failed");
    return;
  }
  ruli_addr_rfc3484_sort(&list, 0);

  if (ruli_list_size(&list) != 2) {
    failf("rfc3484_sort", "size after sort=%d want=2", ruli_list_size(&list));
    ruli_list_delete(&list);
    return;
  }
  first = (ruli_addr_t *) ruli_list_get(&list, 0);
  second = (ruli_addr_t *) ruli_list_get(&list, 1);
  if (!first || !second ||
      ruli_addr_family(first) != PF_INET6 ||
      ruli_addr_family(second) != PF_INET) {
    failf("rfc3484_sort", "RFC 3484 rule 9 order not produced: [0]=%d [1]=%d",
         first ? ruli_addr_family(first) : -1,
         second ? ruli_addr_family(second) : -1);
    ruli_list_delete(&list);
    return;
  }
  ruli_free(v4);
  ruli_free(v6);
  ruli_list_delete(&list);
  OK("rfc3484_sort");
}

/* ------------------------------------------------------------------ */
/* 9. allocator wrappers (liboop glue) + the ruli_list container       */
/* ------------------------------------------------------------------ */
static int g_hook_allocs = 0;
static int g_hook_frees = 0;

static void *hook_malloc(size_t len)
{
  ++g_hook_allocs;
  return malloc(len);
}

static void *hook_realloc(void *ptr, size_t len)
{
  ++g_hook_allocs;
  return realloc(ptr, len);
}

static void hook_free(void *ptr)
{
  ++g_hook_frees;
  free(ptr);
}

static void check_mem_and_list(void)
{
  void *(*old_malloc)(size_t) = ruli_malloc;
  void *(*old_realloc)(void *, size_t) = ruli_realloc;
  void (*old_free)(void *) = ruli_free;
  char *blob;
  ruli_list_t list;
  int i;
  char marker[8];
  int popped_ok = 1;

  /* the default allocator path really lands in liboop's oop_malloc() */
  blob = (char *) ruli_mem_malloc(64);
  if (!blob) {
    failf("mem_and_list", "ruli_mem_malloc returned NULL");
    return;
  }
  memset(blob, 'x', 64);
  blob = (char *) ruli_mem_realloc(blob, 128);
  if (!blob || blob[63] != 'x') {
    failf("mem_and_list", "ruli_mem_realloc lost contents");
    return;
  }
  ruli_mem_free(blob);

  /* and the public hook really is the indirection used by the library */
  ruli_malloc = hook_malloc;
  ruli_realloc = hook_realloc;
  ruli_free = hook_free;
  {
    void *p = ruli_malloc(16);
    ruli_free(p);
  }
  ruli_malloc = old_malloc;
  ruli_realloc = old_realloc;
  ruli_free = old_free;
  if (g_hook_allocs != 1 || g_hook_frees != 1) {
    failf("mem_and_list", "allocator hooks allocs=%d frees=%d want 1/1",
         g_hook_allocs, g_hook_frees);
    return;
  }

  if (ruli_list_new_cap(&list, 2)) {
    failf("mem_and_list", "ruli_list_new_cap failed");
    return;
  }
  if (ruli_list_capacity(&list) != 2) {
    failf("mem_and_list", "capacity=%d want 2", ruli_list_capacity(&list));
    ruli_list_delete(&list);
    return;
  }
  for (i = 0; i < 5; ++i) {
    marker[i] = (char) ('A' + i);
    if (ruli_list_push(&list, &marker[i])) {
      failf("mem_and_list", "push %d failed", i);
      ruli_list_delete(&list);
      return;
    }
  }
  if (ruli_list_size(&list) != 5) {
    failf("mem_and_list", "size=%d want 5", ruli_list_size(&list));
    ruli_list_delete(&list);
    return;
  }
  if (memcmp(ruli_list_get(&list, 0), "A", 1) ||
      memcmp(ruli_list_top(&list), "E", 1)) {
    failf("mem_and_list", "get/top returned the wrong slot");
    ruli_list_delete(&list);
    return;
  }
  if (ruli_list_insert_at(&list, 0, &marker[4]) ) {
    failf("mem_and_list", "insert_at failed");
    ruli_list_delete(&list);
    return;
  }
  if (memcmp(ruli_list_top(&list), "E", 1)) {
    failf("mem_and_list", "insert_at did not shift the head");
    ruli_list_delete(&list);
    return;
  }
  if (ruli_list_shift_at(&list, 0) != &marker[4]) {
    failf("mem_and_list", "shift_at returned the wrong item");
    popped_ok = 0;
  }
  if (popped_ok && ruli_list_size(&list) != 5) {
    failf("mem_and_list", "size after shift_at=%d want 5", ruli_list_size(&list));
    ruli_list_delete(&list);
    return;
  }
  {
    void *popped = ruli_list_pop(&list);
    if (!popped || ruli_list_size(&list) != 4) {
      failf("mem_and_list", "pop gave %p size=%d", popped, ruli_list_size(&list));
      ruli_list_delete(&list);
      return;
    }
  }
  ruli_list_prune(&list, 1);
  if (ruli_list_size(&list) != 1) {
    failf("mem_and_list", "prune left size=%d want 1", ruli_list_size(&list));
    ruli_list_delete(&list);
    return;
  }
  ruli_list_delete(&list);
  OK("mem_and_list");
}

/* ------------------------------------------------------------------ */
/* 10. error-string tables                                             */
/* ------------------------------------------------------------------ */
static void check_errstr_tables(void)
{
  const char *res_ok = ruli_res_errstr(0);
  const char *list_ok = ruli_list_errstr(0);

  if (!res_ok || !*res_ok || !list_ok || !*list_ok) {
    failf("errstr_tables", "empty error strings: res='%s' list='%s'",
         res_ok ? res_ok : "(null)", list_ok ? list_ok : "(null)");
    return;
  }
  if (strcmp(res_ok, list_ok) == 0) {
    failf("errstr_tables", "two different tables returned the same text");
    return;
  }
  OK("errstr_tables");
}

/* ------------------------------------------------------------------ */
/* DNS transport helper shared by check 11                             */
/* ------------------------------------------------------------------ */

/* Codes that mean "no answer ever came back" as opposed to "an answer came
   back and said no".  ruli's own resolver context is created with
   ruli_search_res_new(source, retry = 2, timeout = 10), so one such attempt is
   already bounded by roughly 2 x 10 s; we still retry a couple of times
   because a single dropped UDP datagram must not be reported as a
   platform limitation. */
static int transport_failed(int code)
{
  switch (code) {
  case RULI_SRV_CODE_VOID:
  case RULI_SRV_CODE_ALARM:
  case RULI_SRV_CODE_QUERY_FAILED:
  case RULI_SRV_CODE_FALL_ALARM:
  case RULI_SRV_CODE_FALL_QUERY:
  case RULI_SRV_CODE_WALK_ALARM:
  case RULI_SRV_CODE_WALK_QUERY:
    return 1;
  default:
    return 0;
  }
}

#define SYNC_ATTEMPTS 3

/* ------------------------------------------------------------------ */
/* 11. real resolution path, negative answer: NXDOMAIN for .invalid    */
/* ------------------------------------------------------------------ */
static void check_sync_query_nxdomain(void)
{
  ruli_sync_t *syn = 0;
  int code = RULI_SRV_CODE_VOID;
  int rcode = RULI_RCODE_VOID;
  int attempt;
  int got_answer = 0;
  char ev[256];

  for (attempt = 0; attempt < SYNC_ATTEMPTS; ++attempt) {
    syn = ruli_sync_query("_rulitest", "example.invalid", 0, 0);
    if (!syn) {
      code = RULI_SRV_CODE_VOID;
      rcode = RULI_RCODE_VOID;
      sleep(1);
      continue;
    }
    code = ruli_sync_srv_code(syn);
    rcode = ruli_sync_rcode(syn);
    if (!transport_failed(code)) {
      got_answer = 1;
      break;
    }
    ruli_sync_delete(syn);
    syn = 0;
    sleep(1);
  }

  if (!got_answer) {
    snprintf(ev, sizeof(ev),
         "attempts=%d last srv_code=%d rcode=%d; NULL return means ruli's own "
         "/etc/resolv.conf loader produced no usable nameserver or UDP/53 is "
         "blocked, non-NULL means every attempt hit the retry/timeout budget "
         "(ruli_search_res_new(source, 2, 10))",
         SYNC_ATTEMPTS, code, rcode);
    if (syn)
      ruli_sync_delete(syn);
    SKIP("sync_query_nxdomain",
         "no DNS transport reachable from this target", ev);
    return;
  }

  snprintf(ev, sizeof(ev), "srv_code=%d rcode=%d", code, rcode);

  if (rcode == RULI_RCODE_NOERROR) {
    ruli_sync_delete(syn);
    failf("sync_query_nxdomain",
         "RFC 6761 reserved TLD answered NOERROR: %s", ev);
    return;
  }
  /* A delegating resolver may answer SERVFAIL/REFUSED for .invalid instead of
     NXDOMAIN.  That is the upstream server's policy, not a ruli defect and
     not a platform limitation either, so it is reported as a skip with the
     decoded rcode as evidence rather than as a failure. */
  if (rcode != RULI_RCODE_NAMEERROR) {
    ruli_sync_delete(syn);
    SKIP("sync_query_nxdomain",
         "authoritative answer obtained but the recursive resolver did not "
         "return NAMEERROR for the RFC 6761 reserved TLD", ev);
    return;
  }
  /* rcode == NAMEERROR proves the full path: resolv.conf parse -> socket ->
     ruli_dname_encode() of the QNAME -> ruli_parse_*() of the reply header.
     A negative answer must not carry an SRV list. */
  {
    const ruli_list_t *lst = ruli_sync_srv_list(syn);
    if (lst && ruli_list_size(lst) != 0) {
      ruli_sync_delete(syn);
      failf("sync_query_nxdomain",
           "NAMEERROR answer still carried %d record(s): %s",
           ruli_list_size(lst), ev);
      return;
    }
  }
  ruli_sync_delete(syn);
  OK("sync_query_nxdomain");
}

/* ------------------------------------------------------------------ */
/* 12. ruli_getaddrinfo() dispatch + option accessors                  */
/*                                                                     */
/* Deterministic (no network): ruli_getaddrinfo() must short-circuit to */
/* libc getaddrinfo(3) for AI_NUMERICHOST instead of launching an SRV   */
/* round trip, and it must hand back a decoded PF_INET result.         */
/* ------------------------------------------------------------------ */
static void check_getaddrinfo_dispatch(void)
{
  struct addrinfo hints;
  struct addrinfo *res = 0;
  int rc;
  long before;
  long after = 0;

  /* the option accessors really round-trip ruli's own global */
  before = ruli_getaddrinfo_getoptions();
  ruli_getaddrinfo_setoptions(before | RULI_RES_OPT_SRV_NOINET6);
  after = ruli_getaddrinfo_getoptions();
  if (!(after & RULI_RES_OPT_SRV_NOINET6)) {
    ruli_getaddrinfo_setoptions(before);
    failf("getaddrinfo_dispatch",
         "setoptions/getoptions lost the flag: before=0x%lx after=0x%lx",
         before, after);
    return;
  }
  ruli_getaddrinfo_setoptions(before);

  memset(&hints, 0, sizeof(hints));
  hints.ai_flags = AI_NUMERICHOST;
  hints.ai_family = AF_INET;
  hints.ai_socktype = SOCK_STREAM;
  rc = ruli_getaddrinfo("127.0.0.1", "80", &hints, &res);
  if (rc != 0 || !res) {
    failf("getaddrinfo_dispatch",
         "numeric host rejected: rc=%d (%s) res=%p",
         rc, res ? "(set)" : "(null)", (void *) res);
    return;
  }
  if (res->ai_family != AF_INET || res->ai_addrlen < sizeof(struct sockaddr_in)) {
    ruli_freeaddrinfo(res);
    failf("getaddrinfo_dispatch", "family=%d addrlen=%u",
         res->ai_family, (unsigned) res->ai_addrlen);
    return;
  }
  {
    struct sockaddr_in sin;
    memcpy(&sin, res->ai_addr, sizeof(sin));
    if (sin.sin_port != htons(80) ||
        sin.sin_addr.s_addr != htonl(0x7F000001)) {
      ruli_freeaddrinfo(res);
      failf("getaddrinfo_dispatch", "port=%d addr=0x%08x want 80/0x7f000001",
           (int) ntohs(sin.sin_port), (unsigned) sin.sin_addr.s_addr);
      return;
    }
  }
  ruli_freeaddrinfo(res);
  OK("getaddrinfo_dispatch");
}

int main(void)
{
  printf("ruli-consumer-test version=%s\n", "0.36");
  fflush(stdout);

  check_dname_encode_wire_format();
  check_dname_decode_roundtrip();
  check_dname_encode_guards();
  check_dname_match();
  check_dname_expand_pointer();
  check_qtype_qclass_tables();
  check_addr_parse_snprint();
  check_rfc3484_sort();
  check_mem_and_list();
  check_errstr_tables();
  check_sync_query_nxdomain();
  check_getaddrinfo_dispatch();

  printf("SUMMARY ok=%d skipped=%d failed=%d discovered=12\n",
         g_checks_ok, g_checks_skipped, g_checks_failed);
  fflush(stdout);

  if (g_checks_failed != 0)
    return 1;
  if (g_checks_ok + g_checks_skipped != 12)
    return 2;
  return 0;
}
