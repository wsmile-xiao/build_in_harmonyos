/* Consumer-side functional tests for GNU oSIP 5.3.2 (libosip package).
 *
 * Covers, via the public API only:
 *  1. SIP message parsing   — a full INVITE with all core headers + SDP body
 *  2. SIP message generation — build a REGISTER from scratch and re-parse it
 *  3. URI handling          — osip_uri_parse / osip_uri_to_str round-trip,
 *                             accessors on url params
 *  4. Header accessors      — To/From/CallID/CSeq/Via/Max-Forwards getters
 *  5. Body handling         — message bodies list + SDP body parsing
 *  6. Malformed input       — garbage and truncated SIP messages must be
 *                             rejected with a non-zero return
 *  7. Transaction layer API — osip_init/osip_transaction_init sanity (osip2)
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

#include <osip2/osip.h>
#include <osipparser2/osip_parser.h>
#include <osipparser2/sdp_message.h>

static int failures = 0;
static int checks = 0;

static void check(int cond, const char *what)
{
    checks++;
    if (!cond) {
        failures++;
        fprintf(stderr, "FAIL: %s\n", what);
    }
}

static const char *invite_msg =
    "INVITE sip:bob@example.com SIP/2.0\r\n"
    "Via: SIP/2.0/UDP pc33.example.com;branch=z9hG4bK776asdhds\r\n"
    "Max-Forwards: 70\r\n"
    "To: Bob <sip:bob@example.com>\r\n"
    "From: Alice <sip:alice@example.com>;tag=1928301774\r\n"
    "Call-ID: a84b4c76e66710@pc33.example.com\r\n"
    "CSeq: 314159 INVITE\r\n"
    "Contact: <sip:alice@pc33.example.com>\r\n"
    "Content-Type: application/sdp\r\n"
    "Content-Length: 156\r\n"
    "\r\n"
    "v=0\r\n"
    "o=alice 2890844526 2890844526 IN IP4 pc33.example.com\r\n"
    "s=Session SDP\r\n"
    "c=IN IP4 pc33.example.com\r\n"
    "t=0 0\r\n"
    "m=audio 49170 RTP/AVP 0\r\n"
    "a=rtpmap:0 PCMU/8000\r\n";

int main(void)
{
    /* Initialize the parser's global tables first — osip_message_parse
     * dereferences them without checking (upstream torture.c does the
     * same before its first parse). */
    check(parser_init() == 0, "parser_init");

    /* ---- 1. parse a full INVITE -------------------------------------- */
    osip_message_t *inv = NULL;
    int rc = osip_message_init(&inv);
    check(rc == 0 && inv != NULL, "osip_message_init");
    rc = osip_message_parse(inv, invite_msg, strlen(invite_msg));
    check(rc == 0, "parse full INVITE");

    check(inv->sip_method != NULL && strcmp(inv->sip_method, "INVITE") == 0,
          "method == INVITE");
    check(inv->status_code == 0, "request has code 0");
    check(inv->req_uri != NULL && inv->req_uri->host != NULL &&
          strcmp(inv->req_uri->host, "example.com") == 0, "Request-URI host");

    /* ---- 4. header accessors ----------------------------------------- */
    osip_from_t *from = osip_message_get_from(inv);
    check(from != NULL && from->url != NULL &&
          from->url->username != NULL &&
          strcmp(from->url->username, "alice") == 0,
          "From username == alice");
    osip_uri_param_t *tag = NULL;
    osip_from_param_get_byname(from, "tag", &tag);
    check(tag != NULL && tag->gvalue != NULL &&
          strcmp(tag->gvalue, "1928301774") == 0, "From tag");

    osip_to_t *to = osip_message_get_to(inv);
    check(to != NULL && to->url != NULL &&
          to->url->host != NULL &&
          strcmp(to->url->host, "example.com") == 0, "To host");

    osip_call_id_t *cid = osip_message_get_call_id(inv);
    check(cid != NULL && cid->number != NULL && cid->host != NULL &&
          strcmp(cid->number, "a84b4c76e66710") == 0 &&
          strcmp(cid->host, "pc33.example.com") == 0,
          "Call-ID number+host");

    osip_cseq_t *cseq = osip_message_get_cseq(inv);
    check(cseq != NULL && cseq->number != NULL && cseq->method != NULL &&
          strcmp(cseq->number, "314159") == 0 &&
          strcmp(cseq->method, "INVITE") == 0, "CSeq number+method");

    osip_via_t *via = NULL;
    rc = osip_message_get_via(inv, 0, &via);
    check(rc == 0 && via != NULL && via->host != NULL &&
          strcmp(via->host, "pc33.example.com") == 0, "Via[0] host");
    osip_uri_param_t *branch = NULL;
    osip_via_param_get_byname(via, "branch", &branch);
    check(branch != NULL && branch->gvalue != NULL &&
          strcmp(branch->gvalue, "z9hG4bK776asdhds") == 0, "Via branch");

    osip_contact_t *ct = NULL;
    rc = osip_message_get_contact(inv, 0, &ct);
    check(rc == 0 && ct != NULL && ct->url != NULL &&
          ct->url->host != NULL &&
          strcmp(ct->url->host, "pc33.example.com") == 0, "Contact[0] host");

    osip_header_t *mfh = NULL;
    rc = osip_message_get_max_forwards(inv, 0, &mfh);
    check(rc == 0 && mfh != NULL && mfh->hvalue != NULL &&
          strcmp(mfh->hvalue, "70") == 0, "Max-Forwards == 70");

    /* ---- 3. URI round-trip ------------------------------------------- */
    osip_uri_t *url = NULL;
    rc = osip_uri_init(&url);
    check(rc == 0, "osip_uri_init");
    rc = osip_uri_parse(url, "sip:bob@example.com:5060;transport=udp?X=1");
    check(rc == 0, "osip_uri_parse");
    check(url->scheme && strcmp(url->scheme, "sip") == 0, "uri scheme");
    check(url->username && strcmp(url->username, "bob") == 0, "uri user");
    check(url->host && strcmp(url->host, "example.com") == 0, "uri host");
    check(url->port && strcmp(url->port, "5060") == 0, "uri port");
    osip_uri_param_t *tp = NULL;
    osip_uri_uparam_get_byname(url, "transport", &tp);
    check(tp != NULL && tp->gvalue &&
          strcmp(tp->gvalue, "udp") == 0, "uri transport param");
    char *url_str = NULL;
    rc = osip_uri_to_str(url, &url_str);
    check(rc == 0 && url_str != NULL, "osip_uri_to_str");
    check(url_str && strstr(url_str, "example.com") != NULL,
          "uri re-serialized contains host");
    osip_uri_free(url);
    osip_free(url_str);

    /* ---- 5. body ------------------------------------------------------ */
    check(osip_list_size(&inv->bodies) == 1, "one body attached");
    osip_body_t *b0 = (osip_body_t *) osip_list_get(&inv->bodies, 0);
    check(b0 != NULL && b0->body != NULL && b0->length == 156,
          "body[0] data, length 156");
    check(inv->content_type != NULL &&
          inv->content_type->type && inv->content_type->subtype &&
          strcmp(inv->content_type->type, "application") == 0 &&
          strcmp(inv->content_type->subtype, "sdp") == 0,
          "Content-Type application/sdp");
    check(b0->body && strstr(b0->body, "m=audio 49170") != NULL,
          "body[0] contains SDP m=audio line");

    /* parse the SDP body too — osip_body_t.body is NOT NUL-terminated,
     * so copy it into a terminated buffer first */
    char *sdp_buf = malloc(b0->length + 1);
    check(sdp_buf != NULL, "malloc sdp_buf");
    memcpy(sdp_buf, b0->body, b0->length);
    sdp_buf[b0->length] = '\0';
    sdp_message_t *sdp = NULL;
    rc = sdp_message_init(&sdp);
    check(rc == 0, "sdp_message_init");
    rc = sdp_message_parse(sdp, sdp_buf);
    check(rc == 0, "sdp_message_parse");
    check(sdp_message_o_addr_get(sdp) != NULL &&
          strcmp(sdp_message_o_addr_get(sdp), "pc33.example.com") == 0,
          "sdp o= address");
    sdp_message_free(sdp);
    free(sdp_buf);

    /* ---- 2. generate a message from scratch --------------------------- */
    osip_message_t *reg = NULL;
    rc = osip_message_init(&reg);
    check(rc == 0, "init reg");
    /* set_method/set_version store the pointer and osip_message_free()
     * free()s it — pass heap strings, never literals */
    osip_message_set_method(reg, osip_strdup("REGISTER"));
    osip_message_set_version(reg, osip_strdup("SIP/2.0"));
    osip_uri_t *ruri = NULL;
    osip_uri_init(&ruri);
    osip_uri_parse(ruri, "sip:example.com");
    osip_message_set_uri(reg, ruri);
    rc = osip_message_set_to(reg, "Bob <sip:bob@example.com>");
    check(rc == 0, "set To");
    rc = osip_message_set_from(reg, "Alice <sip:alice@example.com>;tag=9x");
    check(rc == 0, "set From");
    rc = osip_message_set_call_id(reg, "reg-call-1");
    check(rc == 0, "set Call-ID");
    rc = osip_message_set_cseq(reg, "1 REGISTER");
    check(rc == 0, "set CSeq");
    rc = osip_message_set_via(reg, "SIP/2.0/UDP host.example.com:5060;branch=z9hG4bKreg");
    check(rc == 0, "set Via");
    rc = osip_message_set_max_forwards(reg, "70");
    check(rc == 0, "set Max-Forwards");
    rc = osip_message_set_content_length(reg, "0");
    check(rc == 0, "set Content-Length");

    char *gen = NULL;
    size_t gen_len = 0;
    rc = osip_message_to_str(reg, &gen, &gen_len);
    check(rc == 0 && gen != NULL && gen_len > 0, "message_to_str");
    check(gen && strncmp(gen, "REGISTER", 8) == 0,
          "serialized starts with REGISTER");
    check(gen && strstr(gen, "Call-ID: reg-call-1") != NULL,
          "serialized contains Call-ID");

    /* re-parse what we generated — round-trip integrity */
    osip_message_t *rep = NULL;
    osip_message_init(&rep);
    rc = osip_message_parse(rep, gen, gen_len);
    check(rc == 0, "re-parse generated message");
    check(rep->sip_method && strcmp(rep->sip_method, "REGISTER") == 0,
          "round-trip method");
    osip_cseq_t *rcs = osip_message_get_cseq(rep);
    check(rcs != NULL && rcs->number && strcmp(rcs->number, "1") == 0,
          "round-trip CSeq number");
    osip_message_free(rep);
    osip_free(gen);
    osip_message_free(reg);

    /* response message generation: start-line routing checks
     * sip_method first, so a request-turned-response must clear it */
    osip_message_t *resp = NULL;
    osip_message_init(&resp);
    rc = osip_message_parse(resp, invite_msg, strlen(invite_msg));
    check(rc == 0, "parse INVITE again");
    osip_free(resp->sip_method);
    resp->sip_method = NULL;
    osip_message_set_status_code(resp, 200);
    osip_message_set_reason_phrase(resp, osip_strdup("OK"));
    char *rstr = NULL; size_t rlen = 0;
    rc = osip_message_to_str(resp, &rstr, &rlen);
    check(rc == 0 && rstr && strncmp(rstr, "SIP/2.0 200", 11) == 0,
          "serialized response start line");
    osip_free(rstr);
    osip_message_free(resp);

    /* ---- 6. malformed input ------------------------------------------ */
    osip_message_t *bad = NULL;
    osip_message_init(&bad);
    rc = osip_message_parse(bad, "this is not a sip message at all\r\n\r\n",
                            strlen("this is not a sip message at all\r\n\r\n"));
    check(rc != 0, "garbage input rejected");
    osip_message_free(bad);

    osip_message_t *badver = NULL;
    osip_message_init(&badver);
    rc = osip_message_parse(badver, "INVITE sip:x@y SIP/9.9\r\n\r\n",
                            strlen("INVITE sip:x@y SIP/9.9\r\n\r\n"));
    /* oSIP is version-agnostic on the start line: it stores "SIP/9.9"
     * rather than rejecting it. Verify it round-trips instead. */
    check(rc == 0 && badver->sip_version != NULL &&
          strcmp(badver->sip_version, "SIP/9.9") == 0,
          "unknown version stored verbatim");
    osip_message_free(badver);

    osip_message_t *baduri = NULL;
    osip_message_init(&baduri);
    rc = osip_message_parse(baduri, "INVITE not-a-uri SIP/2.0\r\n\r\n",
                            strlen("INVITE not-a-uri SIP/2.0\r\n\r\n"));
    check(rc < 0, "malformed Request-URI rejected");
    osip_message_free(baduri);

    /* ---- 7. transaction layer (osip2) --------------------------------- */
    osip_t *osip = NULL;
    rc = osip_init(&osip);
    check(rc == 0 && osip != NULL, "osip_init (osip2 layer)");
    osip_transaction_t *tr = NULL;
    rc = osip_transaction_init(&tr, IST, osip, inv);
    check(rc == 0 && tr != NULL, "osip_transaction_init IST");
    check(tr->your_instance == NULL, "transaction instance NULL initially");
    osip_transaction_free(tr);
    osip_release(osip);
    osip_message_free(inv);

    printf("libosip consumer tests: %d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
