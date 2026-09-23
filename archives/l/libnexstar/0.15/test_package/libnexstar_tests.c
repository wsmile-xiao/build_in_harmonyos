#include <errno.h>
#include <math.h>
#include <poll.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#include <deg2str.h>
#include <nexstar.h>

#define CHECK(condition, message) do { \
    if (!(condition)) { \
        fprintf(stderr, "FAIL: %s\n", message); \
        return 1; \
    } \
} while (0)

static int write_full(int fd, const unsigned char *data, size_t size) {
    size_t offset = 0;
    while (offset < size) {
        ssize_t written = write(fd, data + offset, size - offset);
        if (written <= 0) {
            return -1;
        }
        offset += (size_t)written;
    }
    return 0;
}

static int read_full(int fd, unsigned char *data, size_t size) {
    size_t offset = 0;
    while (offset < size) {
        struct pollfd descriptor = {fd, POLLIN, 0};
        int ready;
        do {
            ready = poll(&descriptor, 1, 3000);
        } while (ready < 0 && errno == EINTR);
        if (ready <= 0 || !(descriptor.revents & POLLIN)) {
            return -1;
        }
        ssize_t received = read(fd, data + offset, size - offset);
        if (received <= 0) {
            return -1;
        }
        offset += (size_t)received;
    }
    return 0;
}

static int configure_mount(int fd, int version, int vendor) {
    if (enforce_protocol_version(fd, version) != RC_OK) {
        return -1;
    }
    /* The upstream vendor selector is process-global and takes no fd. */
    if (enforce_vendor_protocol(vendor) != vendor) {
        return -1;
    }
    return 0;
}

static int begin_exchange(int pair[2], const unsigned char *reply, size_t reply_size) {
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, pair) != 0) {
        return -1;
    }
    if (write_full(pair[1], reply, reply_size) != 0) {
        close(pair[0]);
        close(pair[1]);
        return -1;
    }
    return 0;
}

static int finish_exchange(int pair[2], const unsigned char *command, size_t command_size) {
    unsigned char actual[32];
    int result = 0;
    if (command_size > sizeof(actual) || read_full(pair[1], actual, command_size) != 0 ||
        memcmp(actual, command, command_size) != 0) {
        result = -1;
    }
    close(pair[0]);
    close(pair[1]);
    return result;
}

static int exchange_slew(char axis, char direction, char rate,
                         unsigned char axis_id, unsigned char command_id) {
    const unsigned char reply[] = {'#'};
    const unsigned char expected[] = {'P', 2, axis_id, command_id,
                                      (unsigned char)rate, 0, 0, 0};
    int pair[2];
    CHECK(begin_exchange(pair, reply, sizeof(reply)) == 0, "create slew transport");
    CHECK(configure_mount(pair[0], VER_4_10, VNDR_CELESTRON) == 0,
          "configure slew protocol failed");
    CHECK(tc_slew_fixed(pair[0], axis, direction, rate) == RC_OK,
          "fixed slew command failed");
    CHECK(finish_exchange(pair, expected, sizeof(expected)) == 0,
          "fixed slew command bytes differ");
    return 0;
}

static int test_celtest(void) {
    const unsigned char reply[] = {1, '#'};
    const unsigned char expected[] = {'J'};
    int pair[2];
    CHECK(begin_exchange(pair, reply, sizeof(reply)) == 0, "create alignment transport");
    CHECK(configure_mount(pair[0], VER_4_10, VNDR_CELESTRON) == 0,
          "configure alignment protocol failed");
    CHECK(tc_check_align(pair[0]) == 1, "alignment response was not decoded");
    CHECK(finish_exchange(pair, expected, sizeof(expected)) == 0,
          "alignment command differs");
    return 0;
}

static int test_nexstarctl(void) {
    int pair[2];
    char model_name[32];
    char major = 0;
    char minor = 0;

    const unsigned char orientation_reply[] = {'N', '#'};
    const unsigned char orientation_command[] = {'p'};
    CHECK(begin_exchange(pair, orientation_reply, sizeof(orientation_reply)) == 0,
          "create orientation transport");
    CHECK(configure_mount(pair[0], VER_3_37_8, VNDR_SKYWATCHER) == 0,
          "configure orientation protocol failed");
    CHECK(tc_get_orientation(pair[0]) == 'N', "orientation response differs");
    CHECK(finish_exchange(pair, orientation_command, sizeof(orientation_command)) == 0,
          "orientation command differs");

    const unsigned char model_reply[] = {9, '#'};
    const unsigned char model_command[] = {'m'};
    CHECK(begin_exchange(pair, model_reply, sizeof(model_reply)) == 0,
          "create model transport");
    CHECK(configure_mount(pair[0], VER_4_10, VNDR_CELESTRON) == 0,
          "configure model protocol failed");
    CHECK(tc_get_model(pair[0]) == 9, "model response differs");
    CHECK(finish_exchange(pair, model_command, sizeof(model_command)) == 0,
          "model command differs");
    CHECK(get_model_name(9, model_name, sizeof(model_name)) == model_name,
          "model name lookup failed");
    CHECK(strcmp(model_name, "CPC") == 0, "model name differs");

    const unsigned char version_reply[] = {4, 10, '#'};
    const unsigned char version_command[] = {'V'};
    CHECK(begin_exchange(pair, version_reply, sizeof(version_reply)) == 0,
          "create version transport");
    CHECK(configure_mount(pair[0], VER_4_10, VNDR_CELESTRON) == 0,
          "configure version protocol failed");
    CHECK(tc_get_version(pair[0], &major, &minor) == VER_4_10,
          "protocol version differs");
    CHECK(major == 4 && minor == 10, "protocol version bytes differ");
    CHECK(finish_exchange(pair, version_command, sizeof(version_command)) == 0,
          "version command differs");
    return 0;
}

static int test_nexstarctl2(void) {
    int pair[2];
    const unsigned char get_reply[] = {NX_TC_TRACK_EQ_NORTH, '#'};
    const unsigned char get_command[] = {'t'};
    const unsigned char set_reply[] = {'#'};
    const unsigned char set_command[] = {'T', NX_TC_TRACK_OFF};

    CHECK(begin_exchange(pair, get_reply, sizeof(get_reply)) == 0,
          "create tracking query transport");
    CHECK(configure_mount(pair[0], VER_4_10, VNDR_CELESTRON) == 0,
          "configure tracking query protocol failed");
    CHECK(tc_get_tracking_mode(pair[0]) == TC_TRACK_EQ_NORTH,
          "tracking mode response differs");
    CHECK(finish_exchange(pair, get_command, sizeof(get_command)) == 0,
          "tracking query command differs");

    CHECK(begin_exchange(pair, set_reply, sizeof(set_reply)) == 0,
          "create tracking update transport");
    CHECK(configure_mount(pair[0], VER_4_10, VNDR_CELESTRON) == 0,
          "configure tracking update protocol failed");
    CHECK(tc_set_tracking_mode(pair[0], TC_TRACK_OFF) == RC_OK,
          "tracking mode update failed");
    CHECK(finish_exchange(pair, set_command, sizeof(set_command)) == 0,
          "tracking update command differs");
    CHECK(tc_set_tracking_mode(-1, 99) == RC_PARAMS,
          "invalid tracking mode was accepted");
    return 0;
}

static int test_get_rade1(void) {
    const unsigned char reply[] = "80000000,E0000000#";
    const unsigned char expected[] = {'e'};
    double ra = 0.0;
    double de = 0.0;
    int pair[2];

    CHECK(begin_exchange(pair, reply, sizeof(reply) - 1) == 0,
          "create coordinate transport");
    CHECK(configure_mount(pair[0], VER_4_10, VNDR_ALL_SUPPORTED) == 0,
          "configure coordinate protocol failed");
    CHECK(tc_get_rade_p(pair[0], &ra, &de) == RC_OK,
          "precise coordinate command failed");
    CHECK(fabs(ra - 180.0) < 0.0001, "right ascension differs");
    CHECK(fabs(de + 45.0) < 0.0001, "declination differs");
    CHECK(finish_exchange(pair, expected, sizeof(expected)) == 0,
          "coordinate command differs");
    return 0;
}

static int test_get_rade2(void) {
    char angle[] = "+12:30:00.0";
    char hours[] = "12:30:00.0";
    double degrees = 0.0;
    double hour_value = 0.0;
    unsigned char degree_part = 0;
    unsigned char minute_part = 0;
    unsigned char second_part = 0;
    char sign = 0;

    CHECK(a2dd(&degrees, angle) == Err_NOERR, "angle parsing failed");
    CHECK(fabs(degrees - 12.5) < 0.0001, "angle parsing result differs");
    CHECK(strcmp(dd2a(-45.5, 1), "-45:30:00.0") == 0,
          "angle formatting differs");
    CHECK(a2dh(&hour_value, hours) == Err_NOERR, "hour parsing failed");
    CHECK(fabs(hour_value - 12.5) < 0.0001, "hour parsing result differs");
    CHECK(strcmp(dh2a(hour_value), "12:30:00.0") == 0,
          "hour formatting differs");
    dd2dms(-22.5, &degree_part, &minute_part, &second_part, &sign);
    CHECK(degree_part == 22 && minute_part == 30 && second_part == 0 && sign == 1,
          "degree/minute/second conversion differs");
    return 0;
}

static int test_push_buttons(void) {
    CHECK(exchange_slew(TC_AXIS_DE, TC_DIR_POSITIVE, 9, 17, 36) == 0,
          "positive declination slew failed");
    CHECK(exchange_slew(TC_AXIS_RA, TC_DIR_POSITIVE, 9, 16, 36) == 0,
          "positive right-ascension slew failed");
    CHECK(exchange_slew(TC_AXIS_DE, TC_DIR_POSITIVE, 0, 17, 36) == 0,
          "declination stop failed");
    CHECK(exchange_slew(TC_AXIS_RA, TC_DIR_POSITIVE, 0, 16, 36) == 0,
          "right-ascension stop failed");
    CHECK(tc_slew_fixed(-1, TC_AXIS_RA, TC_DIR_POSITIVE, 10) == RC_PARAMS,
          "invalid fixed slew rate was accepted");
    return 0;
}

static int test_push_left(void) {
    CHECK(exchange_slew(TC_AXIS_RA, TC_DIR_NEGATIVE, 8, 16, 37) == 0,
          "left slew failed");
    CHECK(exchange_slew(TC_AXIS_RA, TC_DIR_NEGATIVE, 0, 16, 37) == 0,
          "left slew stop failed");
    return 0;
}

int main(int argc, char **argv) {
    struct test_case {
        const char *name;
        int (*run)(void);
    } tests[] = {
        {"celtest", test_celtest},
        {"nexstarctl", test_nexstarctl},
        {"nexstarctl2", test_nexstarctl2},
        {"get_rade1", test_get_rade1},
        {"get_rade2", test_get_rade2},
        {"push_buttons", test_push_buttons},
        {"push_left", test_push_left},
    };
    size_t index;

    CHECK(argc == 2, "expected one upstream scenario name");
    for (index = 0; index < sizeof(tests) / sizeof(tests[0]); ++index) {
        if (strcmp(argv[1], tests[index].name) == 0) {
            int result = tests[index].run();
            if (result == 0) {
                printf("PASS: upstream scenario %s\n", tests[index].name);
            }
            return result;
        }
    }
    fprintf(stderr, "Unknown upstream scenario: %s\n", argv[1]);
    return 2;
}
