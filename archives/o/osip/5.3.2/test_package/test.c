/* Consumer test for osip/5.3.2 on OHOS: parse a SIP INVITE with the real
 * libosipparser2 API and assert the decoded fields. Exit code 0 = pass. */
#include <stdio.h>
#include <string.h>

#include <osipparser2/osip_parser.h>

static const char *INVITE_MSG =
    "INVITE sip:bob@example.com SIP/2.0\r\n"
    "Via: SIP/2.0/UDP pc33.example.com;branch=z9hG4bK776asdhds\r\n"
    "To: <sip:bob@example.com>\r\n"
    "From: Alice <sip:alice@example.com>;tag=9fxj76cb\r\n"
    "Call-ID: 3848276298220188511@example.com\r\n"
    "CSeq: 314159 INVITE\r\n"
    "Max-Forwards: 70\r\n"
    "Content-Length: 0\r\n"
    "\r\n";

int main(void) {
    osip_message_t *sip = NULL;

    if (parser_init() != 0) {
        fprintf(stderr, "FAIL: parser_init\n");
        return 1;
    }
    if (osip_message_init(&sip) != 0) {
        fprintf(stderr, "FAIL: osip_message_init\n");
        return 2;
    }
    if (osip_message_parse(sip, INVITE_MSG, strlen(INVITE_MSG)) != 0) {
        fprintf(stderr, "FAIL: osip_message_parse\n");
        osip_message_free(sip);
        return 3;
    }
    if (sip->sip_method == NULL || strcmp(sip->sip_method, "INVITE") != 0) {
        fprintf(stderr, "FAIL: decoded method is not INVITE\n");
        osip_message_free(sip);
        return 4;
    }
    if (sip->call_id == NULL || sip->call_id->number == NULL ||
        strcmp(sip->call_id->number, "3848276298220188511") != 0 ||
        sip->call_id->host == NULL ||
        strcmp(sip->call_id->host, "example.com") != 0) {
        fprintf(stderr, "FAIL: decoded Call-ID mismatch\n");
        osip_message_free(sip);
        return 5;
    }
    if (sip->cseq == NULL || sip->cseq->method == NULL ||
        strcmp(sip->cseq->method, "INVITE") != 0) {
        fprintf(stderr, "FAIL: decoded CSeq method mismatch\n");
        osip_message_free(sip);
        return 6;
    }
    if (sip->from == NULL || sip->from->url == NULL ||
        sip->from->url->username == NULL ||
        strcmp(sip->from->url->username, "alice") != 0) {
        fprintf(stderr, "FAIL: decoded From user mismatch\n");
        osip_message_free(sip);
        return 7;
    }
    osip_message_free(sip);
    printf("test osip 5.3.2: consumer test OK (INVITE parsed, 6 assertions)\n");
    return 0;
}
