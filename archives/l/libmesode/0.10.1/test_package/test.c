/* test_package consumer for libmesode 0.10.1.
 * Exercises the real xmpp_* public API (R34: must call the package API).
 * Each stage returns a distinct exit code; success prints the assertion
 * count line parsed by test_package/conanfile.py for HMBS evidence.
 */
#include <stdio.h>
#include <string.h>

#include <mesode.h>

int main(void)
{
    unsigned int assertions = 0;
    xmpp_ctx_t *ctx = NULL;
    xmpp_stanza_t *st = NULL;
    xmpp_stanza_t *msg = NULL;
    char *jid = NULL;
    char *bare = NULL;
    char *digest = NULL;
    char *b64 = NULL;
    char *uuid = NULL;
    char *body = NULL;

    xmpp_initialize();

    /* 1. version check for 0.10 API. */
    if (!xmpp_version_check(0, 10)) {
        fprintf(stderr, "xmpp_version_check(0,10) failed\n");
        return 1;
    }
    assertions += 1;

    /* 2. context lifecycle. */
    ctx = xmpp_ctx_new(NULL, NULL);
    if (ctx == NULL) {
        fprintf(stderr, "xmpp_ctx_new returned NULL\n");
        xmpp_shutdown();
        return 2;
    }
    assertions += 1;

    /* 3. stanza create + set/get name. */
    st = xmpp_stanza_new(ctx);
    if (st == NULL) {
        fprintf(stderr, "xmpp_stanza_new returned NULL\n");
        return 3;
    }
    if (xmpp_stanza_set_name(st, "message") != XMPP_EOK) {
        fprintf(stderr, "xmpp_stanza_set_name failed\n");
        return 4;
    }
    if (xmpp_stanza_get_name(st) == NULL ||
        strcmp(xmpp_stanza_get_name(st), "message") != 0) {
        fprintf(stderr, "xmpp_stanza_get_name mismatch\n");
        return 5;
    }
    assertions += 2;

    /* 4. stanza text via a child text node (upstream stanza.c:
     * xmpp_stanza_set_text on a TAG stanza fails with XMPP_EINVOP;
     * only a TEXT stanza accepts set_text, same pattern as
     * xmpp_message_set_body which creates body + text child). */
    {
        xmpp_stanza_t *txt = xmpp_stanza_new(ctx);
        char *agg = NULL;
        if (txt == NULL) {
            fprintf(stderr, "text stanza alloc failed\n");
            return 6;
        }
        if (xmpp_stanza_set_text(txt, "hello") != XMPP_EOK) {
            fprintf(stderr, "xmpp_stanza_set_text failed\n");
            xmpp_stanza_release(txt);
            return 6;
        }
        if (xmpp_stanza_get_text_ptr(txt) == NULL ||
            strcmp(xmpp_stanza_get_text_ptr(txt), "hello") != 0) {
            fprintf(stderr, "xmpp_stanza_get_text_ptr mismatch\n");
            xmpp_stanza_release(txt);
            return 7;
        }
        if (xmpp_stanza_add_child(st, txt) != XMPP_EOK) {
            fprintf(stderr, "xmpp_stanza_add_child failed\n");
            xmpp_stanza_release(txt);
            return 6;
        }
        xmpp_stanza_release(txt);
        agg = xmpp_stanza_get_text(st);
        if (agg == NULL || strcmp(agg, "hello") != 0) {
            fprintf(stderr, "xmpp_stanza_get_text mismatch\n");
            if (agg != NULL)
                xmpp_free(ctx, agg);
            return 7;
        }
        xmpp_free(ctx, agg);
    }
    assertions += 1;
    xmpp_stanza_release(st);
    st = NULL;

    /* 5. JID compose + bare JID strips resource. */
    jid = xmpp_jid_new(ctx, "node", "example.com", "res");
    if (jid == NULL || strstr(jid, "node@example.com/res") == NULL) {
        fprintf(stderr, "xmpp_jid_new mismatch: %s\n", jid ? jid : "(null)");
        return 8;
    }
    assertions += 1;
    bare = xmpp_jid_bare(ctx, jid);
    if (bare == NULL || strcmp(bare, "node@example.com") != 0) {
        fprintf(stderr, "xmpp_jid_bare mismatch: %s\n", bare ? bare : "(null)");
        return 9;
    }
    assertions += 1;
    xmpp_free(ctx, jid);
    xmpp_free(ctx, bare);
    jid = NULL;
    bare = NULL;

    /* 6. SHA1 of "abc" is the well-known digest. */
    digest = xmpp_sha1(ctx, (const unsigned char *)"abc", 3);
    if (digest == NULL ||
        strcmp(digest, "a9993e364706816aba3e25717850c26c9cd0d89d") != 0) {
        fprintf(stderr, "xmpp_sha1 mismatch: %s\n", digest ? digest : "(null)");
        return 10;
    }
    assertions += 1;
    xmpp_free(ctx, digest);
    digest = NULL;

    /* 7. Base64 of "hello" per RFC 4648. */
    b64 = xmpp_base64_encode(ctx, (const unsigned char *)"hello", 5);
    if (b64 == NULL || strcmp(b64, "aGVsbG8=") != 0) {
        fprintf(stderr, "xmpp_base64_encode mismatch: %s\n", b64 ? b64 : "(null)");
        return 11;
    }
    assertions += 1;
    xmpp_free(ctx, b64);
    b64 = NULL;

    /* 8. UUID has canonical 36-char text form. */
    uuid = xmpp_uuid_gen(ctx);
    if (uuid == NULL || strlen(uuid) != 36) {
        fprintf(stderr, "xmpp_uuid_gen bad length\n");
        return 12;
    }
    assertions += 1;

    /* 9. Message stanza body helper round-trip. */
    msg = xmpp_message_new(ctx, "chat", "to@example.com", "id1");
    if (msg == NULL) {
        fprintf(stderr, "xmpp_message_new returned NULL\n");
        return 13;
    }
    if (xmpp_message_set_body(msg, "hi") != XMPP_EOK) {
        fprintf(stderr, "xmpp_message_set_body failed\n");
        return 14;
    }
    body = xmpp_message_get_body(msg);
    if (body == NULL || strcmp(body, "hi") != 0) {
        fprintf(stderr, "xmpp_message_get_body mismatch\n");
        return 15;
    }
    assertions += 1;
    xmpp_free(ctx, body);
    xmpp_free(ctx, uuid);
    xmpp_stanza_release(msg);

    xmpp_ctx_free(ctx);
    xmpp_shutdown();

    if (assertions != 11) {
        fprintf(stderr, "assertion miscount: %u\n", assertions);
        return 16;
    }
    printf("libmesode API assertions: %u passed\n", assertions);
    return 0;
}
