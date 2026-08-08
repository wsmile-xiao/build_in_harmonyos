#include <X11/SM/SMlib.h>

#include <stdio.h>

static void client_handler_a(SmcConn connection, Bool swap, int minor_opcode,
                             unsigned long sequence, int error_class,
                             int severity, SmPointer values) {
    (void)connection;
    (void)swap;
    (void)minor_opcode;
    (void)sequence;
    (void)error_class;
    (void)severity;
    (void)values;
}

static void client_handler_b(SmcConn connection, Bool swap, int minor_opcode,
                             unsigned long sequence, int error_class,
                             int severity, SmPointer values) {
    client_handler_a(connection, swap, minor_opcode, sequence, error_class,
                     severity, values);
}

static void manager_handler_a(SmsConn connection, Bool swap, int minor_opcode,
                              unsigned long sequence, int error_class,
                              int severity, SmPointer values) {
    (void)connection;
    (void)swap;
    (void)minor_opcode;
    (void)sequence;
    (void)error_class;
    (void)severity;
    (void)values;
}

static void manager_handler_b(SmsConn connection, Bool swap, int minor_opcode,
                              unsigned long sequence, int error_class,
                              int severity, SmPointer values) {
    manager_handler_a(connection, swap, minor_opcode, sequence, error_class,
                      severity, values);
}

int main(void) {
    SmcErrorHandler original_client;
    SmsErrorHandler original_manager;
    int result = 0;

    original_client = SmcSetErrorHandler(client_handler_a);
    if (SmcSetErrorHandler(client_handler_b) != client_handler_a) {
        fprintf(stderr, "client handler registration did not round-trip\n");
        result = 1;
    }
    if (SmcSetErrorHandler(original_client) != client_handler_b) {
        fprintf(stderr, "client handler restoration did not round-trip\n");
        result = 2;
    }

    original_manager = SmsSetErrorHandler(manager_handler_a);
    if (SmsSetErrorHandler(manager_handler_b) != manager_handler_a) {
        fprintf(stderr, "manager handler registration did not round-trip\n");
        result = 3;
    }
    if (SmsSetErrorHandler(original_manager) != manager_handler_b) {
        fprintf(stderr, "manager handler restoration did not round-trip\n");
        result = 4;
    }

    if (SmProtoMajor != 1 || SmProtoMinor != 0 || SmSaveBoth != 2 ||
        SmRestartNever != 3 || SM_SaveComplete != 18) {
        fprintf(stderr, "public protocol constants changed\n");
        result = 5;
    }

    if (result == 0) {
        puts("LIBSM_TEST handler_contract PASS");
    }
    return result;
}
