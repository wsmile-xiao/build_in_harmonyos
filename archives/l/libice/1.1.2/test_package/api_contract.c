#include <X11/ICE/ICElib.h>
#include <X11/ICE/ICEutil.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void test_error_handler(IceConn connection, Bool swap,
                               int minor_opcode, unsigned long sequence,
                               int error_class, int severity,
                               IcePointer values) {
    (void)connection;
    (void)swap;
    (void)minor_opcode;
    (void)sequence;
    (void)error_class;
    (void)severity;
    (void)values;
}

int main(void) {
    static const char expected_path[] = "libice-explicit-authority";
    IceErrorHandler previous_handler;
    char *cookie;
    char *path;
    int has_nonzero = 0;
    int index;

    path = IceAuthFileName();
    if (path == NULL) {
        fprintf(stderr, "IceAuthFileName returned NULL\n");
        return 1;
    }
    if (strcmp(path, expected_path) != 0) {
        fprintf(stderr, "IceAuthFileName ignored ICEAUTHORITY\n");
        return 2;
    }

    cookie = IceGenerateMagicCookie(32);
    if (cookie == NULL) {
        fprintf(stderr, "IceGenerateMagicCookie returned NULL\n");
        return 3;
    }
    for (index = 0; index < 32; ++index) {
        if ((unsigned char)cookie[index] != 0) {
            has_nonzero = 1;
            break;
        }
    }
    if (!has_nonzero) {
        fprintf(stderr, "IceGenerateMagicCookie returned only zero bytes\n");
        free(cookie);
        return 4;
    }
    free(cookie);

    previous_handler = IceSetErrorHandler(test_error_handler);
    if (IceSetErrorHandler(previous_handler) != test_error_handler) {
        fprintf(stderr, "IceSetErrorHandler did not return the active handler\n");
        return 5;
    }
    IceFreeAuthFileEntry(NULL);
    puts("LIBICE_TEST api_contract PASS");
    return 0;
}
