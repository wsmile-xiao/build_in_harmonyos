#include <inttypes.h>
#include <stdio.h>
#include <string.h>

#include <aws/auth/auth.h>
#include <aws/auth/credentials.h>
#include <aws/common/byte_buf.h>
#include <aws/common/common.h>

static void init_libraries(struct aws_allocator *allocator) {
    aws_common_library_init(allocator);
    aws_common_fatal_assert_library_initialized();
    aws_auth_library_init(allocator);
}

static void clean_up_libraries(void) {
    aws_auth_library_clean_up();
    aws_common_library_clean_up();
}

static int cursor_equals_c_str(struct aws_byte_cursor cursor, const char *expected) {
    const size_t expected_len = strlen(expected);
    return cursor.len == expected_len && memcmp(cursor.ptr, expected, expected_len) == 0;
}

static int check_init(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }

    init_libraries(allocator);
    clean_up_libraries();
    return 0;
}

static int check_static_credentials(void) {
    struct aws_allocator *allocator = aws_default_allocator();
    if (allocator == NULL) {
        return 1;
    }

    init_libraries(allocator);

    struct aws_byte_cursor access_key = aws_byte_cursor_from_c_str("AKIDEXAMPLE");
    struct aws_byte_cursor secret_key = aws_byte_cursor_from_c_str("wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY");
    struct aws_byte_cursor session_token = aws_byte_cursor_from_c_str("token-example");
    const uint64_t expiration = 1893456000ULL;

    struct aws_credentials *credentials = aws_credentials_new(
        allocator, access_key, secret_key, session_token, expiration);
    if (credentials == NULL) {
        clean_up_libraries();
        return 1;
    }

    int failed = 0;
    if (!cursor_equals_c_str(aws_credentials_get_access_key_id(credentials), "AKIDEXAMPLE")) {
        failed = 1;
    }
    if (!cursor_equals_c_str(aws_credentials_get_secret_access_key(credentials),
            "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY")) {
        failed = 1;
    }
    if (!cursor_equals_c_str(aws_credentials_get_session_token(credentials), "token-example")) {
        failed = 1;
    }
    if (aws_credentials_get_expiration_timepoint_seconds(credentials) != expiration) {
        failed = 1;
    }

    aws_credentials_release(credentials);
    clean_up_libraries();
    return failed;
}

static int run_named_test(const char *mode) {
    if (strcmp(mode, "--init") == 0) {
        return check_init();
    }
    if (strcmp(mode, "--credentials") == 0) {
        return check_static_credentials();
    }
    fprintf(stderr, "unknown test mode: %s\n", mode);
    return 1;
}

int main(int argc, char **argv) {
    if (argc == 2) {
        return run_named_test(argv[1]);
    }

    if (check_init() != 0) {
        return 1;
    }
    if (check_static_credentials() != 0) {
        return 1;
    }

    printf("aws-c-auth package tests OK\n");
    return 0;
}
