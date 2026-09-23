#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "c-client/c-client.h"

/* HMBS: c-client requires application to provide mm_* callbacks.
   Minimal stubs to satisfy linker; cpystr/search tests do not trigger callbacks,
   but linking pulls mail.o/unix.o which references all these symbols. */
void mm_searched(MAILSTREAM *stream, unsigned long number) { (void)stream; (void)number; }
void mm_exists(MAILSTREAM *stream, unsigned long number) { (void)stream; (void)number; }
void mm_expunged(MAILSTREAM *stream, unsigned long number) { (void)stream; (void)number; }
void mm_flags(MAILSTREAM *stream, unsigned long number) { (void)stream; (void)number; }
void mm_notify(MAILSTREAM *stream, char *string, long errflg) { (void)stream; (void)string; (void)errflg; }
void mm_list(MAILSTREAM *stream, int delimiter, char *name, long attributes) { (void)stream; (void)delimiter; (void)name; (void)attributes; }
void mm_lsub(MAILSTREAM *stream, int delimiter, char *name, long attributes) { (void)stream; (void)delimiter; (void)name; (void)attributes; }
void mm_status(MAILSTREAM *stream, char *mailbox, MAILSTATUS *status) { (void)stream; (void)mailbox; (void)status; }
void mm_log(char *string, long errflg) { (void)string; (void)errflg; }
void mm_dlog(char *string) { (void)string; }
void mm_login(NETMBX *mb, char *user, char *pwd, long trial) { (void)mb; (void)trial; if (user) user[0]='\0'; if (pwd) pwd[0]='\0'; }
void mm_critical(MAILSTREAM *stream) { (void)stream; }
void mm_nocritical(MAILSTREAM *stream) { (void)stream; }
long mm_diskerror(MAILSTREAM *stream, long errcode, long serious) { (void)stream; (void)errcode; (void)serious; return NIL; }
void mm_fatal(char *string) { (void)string; }

int main(void) {
    int passed = 0;
    int discovered = 2;
    int failed = 0;

    /* Test 1: header inclusion, version macro and cpystr/fs_give linkage */
    printf("Test 1: c-client header & version/check cpystr/fs_give ... ");
    if (strcmp(CCLIENTVERSION, "2007f") != 0) {
        printf("FAIL (CCLIENTVERSION=%s expected 2007f)\n", CCLIENTVERSION);
        failed++;
    } else {
        char *s = cpystr("c-client-test");
        if (!s) {
            printf("FAIL (cpystr returned NULL)\n");
            failed++;
        } else if (strcmp(s, "c-client-test") != 0) {
            printf("FAIL (cpystr mismatch: got %s)\n", s);
            fs_give((void **)&s);
            failed++;
        } else {
            /* verify fs_give clears pointer */
            fs_give((void **)&s);
            if (s != NULL) {
                printf("FAIL (fs_give did not null pointer)\n");
                failed++;
            } else {
                printf("OK (version=%s cpystr+fs_give ok)\n", CCLIENTVERSION);
                passed++;
            }
        }
    }

    /* Test 2: library functional linkage via ucase/lcase/search */
    printf("Test 2: c-client misc linkage (ucase/lcase/search) ... ");
    {
        unsigned char buf[64];
        strcpy((char *)buf, "HelloWorld");
        ucase(buf);
        if (strcmp((char *)buf, "HELLOWORLD") != 0) {
            printf("FAIL (ucase got %s)\n", buf);
            failed++;
        } else {
            strcpy((char *)buf, "HelloWorld");
            lcase(buf);
            if (strcmp((char *)buf, "helloworld") != 0) {
                printf("FAIL (lcase got %s)\n", buf);
                failed++;
            } else {
                unsigned char *hay = (unsigned char *)"HelloCClientIMAP";
                unsigned char *needle_ok = (unsigned char *)"cclient";
                unsigned char *needle_bad = (unsigned char *)"notfound";
                long r_ok = search(hay, (long)strlen((char *)hay), needle_ok, (long)strlen((char *)needle_ok));
                long r_bad = search(hay, (long)strlen((char *)hay), needle_bad, (long)strlen((char *)needle_bad));
                /* search is case-insensitive, returns T(1) on match, NIL(0) otherwise */
                if (r_ok != T) {
                    printf("FAIL (search expected T got %ld)\n", r_ok);
                    failed++;
                } else if (r_bad != NIL) {
                    printf("FAIL (search bad pattern expected NIL got %ld)\n", r_bad);
                    failed++;
                } else {
                    printf("OK\n");
                    passed++;
                }
            }
        }
    }

    int ok = (failed == 0 && passed == discovered);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"./test_cclient\",\"discovered\":%d,\"passedCount\":%d}\n",
           ok ? "true" : "false", discovered, passed);
    printf("Consumer test: %d/%d passed\n", passed, discovered);
    return ok ? 0 : 1;
}
