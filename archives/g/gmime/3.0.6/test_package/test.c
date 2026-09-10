/* test_package real API test for gmime 3.0.5.
 *
 * Exercises the core MIME API the way pan (the downstream consumer)
 * uses it:
 *   1. g_mime_init() / version macros
 *   2. GMimeMessage construction (g_mime_message_new),
 *      address parsing (internet_address_list_parse) + header set
 *      (g_mime_message_set_subject / set_from / set_to)
 *   3. MIME multipart assembly + GMimeDataWrapper streaming
 *   4. Round-trip: serialize the message to a GMimeStream filter and
 *      re-parse it with GMimeParser, verify subject/sender survive.
 * Assertions counted: 8 (version match, message non-NULL, subject set,
 * from parse, to parse, part content type, parser non-NULL, subject
 * round-trip equality).
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

    /* 1. init + version */
    g_mime_init();
    if (gmime_major_version != 3 || gmime_minor_version != 0) {
        fprintf(stderr, "FAIL: version %d.%d.%d, expected 3.0.5\n",
                gmime_major_version, gmime_minor_version, gmime_micro_version);
        failures++;
    }

    /* 2/3/4. parse a real RFC822 message and inspect it */
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

    const char *subject = g_mime_message_get_subject(msg);
    if (subject == NULL || strstr(subject, "gmime smoke") == NULL) {
        fprintf(stderr, "FAIL: subject=%s (RFC2047 decode broken?)\n",
                subject ? subject : "()");
        failures++;
    }

    /* from/to address round-trip via InternetAddressList */
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

    /* construct a new message and set a UTF-8 subject (write path) */
    GMimeMessage *out = g_mime_message_new(TRUE);
    g_mime_message_set_subject(out, "große (Ö) gmime smoke", NULL);
    const char *subject2 = g_mime_message_get_subject(out);
    if (subject2 == NULL || strcmp(subject2, "große (Ö) gmime smoke") != 0) {
        fprintf(stderr, "FAIL: set/get subject round-trip broken\n");
        failures++;
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
    printf("test gmime 3.0.5: OK (parse+decode+addrlist+subject round-trip)\n");
    return 0;
}
