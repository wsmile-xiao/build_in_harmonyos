/* test_package real API test for gmime 3.2.15.
 *
 * Runs on the OHOS aarch64 target and exercises the core MIME API the way
 * downstream consumers use it:
 *   1. g_mime_init() + version macros (3.2.15 floor)
 *   2. RFC822 parse: GMimeParser on an in-memory stream
 *   3. RFC2047 encoded-word subject decode
 *   4. InternetAddressList From/To handling
 *   5. Write path: g_mime_message_new + UTF-8 subject set/get round-trip
 *   6. GMimeStreamFilter (the filter-pipeline primitive)
 *   7. incremental base64 decode (MIME transfer-encoding primitive)
 *
 * Assertions counted: 10.
 */
#include <gmime/gmime.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    int failures = 0;
    const char *src =
        "From: Alice Example <alice@example.com>\r\n"
        "To: Bob Example <bob@example.org>\r\n"
        "Subject: =?UTF-8?B?Z2xvYmUgKMOH?= gmime smoke\r\n"
        "Date: Mon, 01 Jan 2024 00:00:00 +0000\r\n"
        "Message-Id: <smoke@example.com>\r\n"
        "MIME-Version: 1.0\r\n"
        "Content-Type: text/plain; charset=UTF-8\r\n"
        "\r\n"
        "Hello from gmime test_package.\r\n";

    /* 1. init + version floor */
    g_mime_init();
    if (gmime_major_version != 3 || gmime_minor_version != 2 ||
        gmime_micro_version != 15) {
        fprintf(stderr, "FAIL: version %d.%d.%d, expected 3.2.15\n",
                gmime_major_version, gmime_minor_version, gmime_micro_version);
        failures++;
    }

    /* 2. parse a real RFC822 message */
    GMimeStream *stream = g_mime_stream_mem_new();
    g_mime_stream_write_string(stream, src);
    g_mime_stream_reset(stream);

    GMimeParser *parser = g_mime_parser_new();
    g_mime_parser_init_with_stream(parser, stream);
    GMimeMessage *msg = g_mime_parser_construct_message(parser, NULL);
    if (msg == NULL) {
        fprintf(stderr, "FAIL: parser produced no message\n");
        return 1;
    }

    /* 3. RFC2047 subject decode. The encoded-word "=?UTF-8?B?Z2xvYmUgKMOH?="
     *    must decode to the UTF-8 bytes "globe (\xc3\x87"; the literal text
     *    after it is preserved. Requiring BOTH the decoded bytes present AND
     *    the raw =?...?= marker gone means a passthrough (no decode) fails. */
    const char *subject = g_mime_message_get_subject(msg);
    if (subject == NULL || strstr(subject, "globe (\xc3\x87") == NULL ||
        strstr(subject, "=?UTF-8?B?") != NULL) {
        fprintf(stderr, "FAIL: subject=%s (RFC2047 decode broken?)\n",
                subject ? subject : "()");
        failures++;
    }

    /* 4. From/To address lists */
    InternetAddressList *from = g_mime_message_get_from(msg);
    if (from == NULL || internet_address_list_length(from) != 1) {
        fprintf(stderr, "FAIL: From list length != 1\n");
        failures++;
    }
    const char *addr = NULL;
    if (from != NULL && internet_address_list_length(from) == 1) {
        InternetAddress *ia = internet_address_list_get_address(from, 0);
        addr = internet_address_mailbox_get_addr((InternetAddressMailbox *) ia);
        if (addr == NULL || strcmp(addr, "alice@example.com") != 0) {
            fprintf(stderr, "FAIL: from addr=%s\n", addr ? addr : "()");
            failures++;
        }
    }
    InternetAddressList *to = g_mime_message_get_all_recipients(msg);
    if (to == NULL || internet_address_list_length(to) != 1) {
        fprintf(stderr, "FAIL: To recipients length != 1\n");
        failures++;
    }

    /* 5. write path: new message + UTF-8 subject round-trip */
    GMimeMessage *out = g_mime_message_new(TRUE);
    g_mime_message_set_subject(out, "große (Ö) gmime smoke", NULL);
    const char *subject2 = g_mime_message_get_subject(out);
    if (subject2 == NULL || strcmp(subject2, "große (Ö) gmime smoke") != 0) {
        fprintf(stderr, "FAIL: set/get subject round-trip broken\n");
        failures++;
    }
    if (g_mime_message_get_date(out) != NULL) {
        fprintf(stderr, "FAIL: fresh message unexpectedly carries a date\n");
        failures++;
    }

    /* 6. GMimeStreamFilter: the content-filter pipeline primitive. With no
     *    filter installed it must pass bytes through unchanged.
     *    Ownership: g_mime_stream_filter_new() takes its OWN reference on the
     *    source (gmime/gmime-stream-filter.c: g_object_ref (stream)), i.e. it
     *    does NOT steal the caller's handle. So we hand it a fresh stream and
     *    immediately drop our reference; the filter keeps it alive until the
     *    filter stream itself is released. */
    GMimeStream *wstream = g_mime_stream_mem_new();
    GMimeStream *filtered = g_mime_stream_filter_new(wstream);
    g_object_unref(wstream);
    if (filtered == NULL) {
        fprintf(stderr, "FAIL: g_mime_stream_filter_new returned NULL\n");
        failures++;
    } else {
        if (g_mime_stream_write_string(filtered, "filter-ok") <= 0) {
            fprintf(stderr, "FAIL: write through filter stream failed\n");
            failures++;
        }
        g_object_unref(filtered);
    }

    /* 7. incremental base64 decode: "Z2xvYmUgKMOH" is the RFC2047 payload of
     *    the subject above and must decode to UTF-8 "globe (\xc3\x87". */
    {
        const char *b64 = "Z2xvYmUgKMOH";
        unsigned char outbuf[64];
        int state = 0;
        guint32 save = 0;
        size_t n = g_mime_encoding_base64_decode_step(
            (const unsigned char *) b64, strlen(b64), outbuf, &state, &save);
        if (n != 9 || memcmp(outbuf, "globe (\xc3\x87", 9) != 0) {
            fprintf(stderr, "FAIL: base64 decode produced %zu bytes\n", n);
            failures++;
        }
    }

    g_object_unref(out);
    g_object_unref(msg);
    g_object_unref(parser);
    g_object_unref(stream);
    g_mime_shutdown();

    if (failures > 0) {
        fprintf(stderr, "gmime test FAILED (%d failure(s))\n", failures);
        return 1;
    }
    printf("test gmime 3.2.15: OK (parse+decode+addrlist+subject round-trip)\n");
    return 0;
}
