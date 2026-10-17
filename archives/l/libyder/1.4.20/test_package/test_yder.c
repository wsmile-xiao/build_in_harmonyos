/* Smoke test for libyder 1.4.20 — verify the public logging API works on
 * HarmonyOS PC (aarch64): console/file/callback log modes, levels, date
 * format, newline split. Mirrors the upstream test scenarios from a
 * consumer perspective. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "yder.h"

static int cb_level = Y_LOG_LEVEL_NONE;
static int cb_count = 0;
static char cb_last[512];

static void unit_cb(void * cls, const char * app_name, const time_t date,
                    const unsigned long level, const char * message) {
    (void)cls; (void)app_name; (void)date;
    cb_level = (int)level;
    cb_count++;
    strncpy(cb_last, message, sizeof(cb_last) - 1);
    cb_last[sizeof(cb_last) - 1] = '\0';
}

int main(void) {
    char tmpdir_log[512];
    const char *tmpdir = getenv("TMPDIR");

    /* 1. console mode init/close */
    if (y_init_logs("test_yder_smoke", Y_LOG_MODE_CONSOLE, Y_LOG_LEVEL_DEBUG, NULL,
                    "first test") != 1) {
        fprintf(stderr, "console init failed\n");
        return 1;
    }
    if (y_close_logs() != 1) {
        fprintf(stderr, "console close failed\n");
        return 1;
    }

    /* 2. file mode init + close (write into $TMPDIR, OHOS /tmp is read-only) */
    if (tmpdir == NULL || tmpdir[0] == '\0') {
        tmpdir = ".";
    }
    snprintf(tmpdir_log, sizeof(tmpdir_log), "%s/yder_smoke_test.log", tmpdir);
    if (y_init_logs("test_yder_smoke", Y_LOG_MODE_FILE, Y_LOG_LEVEL_DEBUG, tmpdir_log,
                    "file test") != 1) {
        fprintf(stderr, "file init failed (%s)\n", tmpdir_log);
        return 1;
    }
    y_log_message(Y_LOG_LEVEL_DEBUG, "hello from harmonyos file log");
    if (y_close_logs() != 1) {
        fprintf(stderr, "file close failed\n");
        return 1;
    }

    /* 3. callback mode + level filtering */
    if (y_init_logs("test_yder_smoke", Y_LOG_MODE_CALLBACK, Y_LOG_LEVEL_WARNING, NULL,
                    "callback test") != 1) {
        fprintf(stderr, "callback init failed\n");
        return 1;
    }
    if (y_set_logs_callback(&unit_cb, NULL, "Start callback smoke test") != 1) {
        fprintf(stderr, "set callback failed\n");
        return 1;
    }
    cb_count = 0;
    y_log_message(Y_LOG_LEVEL_DEBUG, "should be filtered out");
    if (cb_count != 0) {
        fprintf(stderr, "DEBUG should be filtered at WARNING level\n");
        return 1;
    }
    y_log_message(Y_LOG_LEVEL_WARNING, "warning passed through");
    if (cb_count != 1 || cb_level != (int)Y_LOG_LEVEL_WARNING) {
        fprintf(stderr, "WARNING not delivered (count=%d level=%d)\n", cb_count, cb_level);
        return 1;
    }
    if (strcmp(cb_last, "warning passed through") != 0) {
        fprintf(stderr, "callback message mismatch: %s\n", cb_last);
        return 1;
    }
    y_log_message(Y_LOG_LEVEL_ERROR, "error passed through");
    if (cb_count != 2 || cb_level != (int)Y_LOG_LEVEL_ERROR) {
        fprintf(stderr, "ERROR not delivered (count=%d level=%d)\n", cb_count, cb_level);
        return 1;
    }

    /* 4. custom date format must be accepted */
    if (y_set_date_format(NULL, "error expected") != 0) {
        fprintf(stderr, "set_date_format(NULL) should fail\n");
        return 1;
    }
    if (y_set_date_format("TEST %Y - :%S", "success") != 1) {
        fprintf(stderr, "set_date_format(valid) failed\n");
        return 1;
    }
    y_log_message(Y_LOG_LEVEL_WARNING, "formatted date line");

    /* 5. newline split must call back once per line */
    if (y_set_split_message_newline(1, "Set newline") != 1) {
        fprintf(stderr, "set_split_message_newline failed\n");
        return 1;
    }
    cb_count = 0;
    y_log_message(Y_LOG_LEVEL_ERROR, "line one\nline two\nline three");
    if (cb_count != 3) {
        fprintf(stderr, "newline split expected 3 callbacks, got %d\n", cb_count);
        return 1;
    }

    if (y_close_logs() != 1) {
        fprintf(stderr, "final close failed\n");
        return 1;
    }

    printf("libyder smoke test PASS\n");
    return 0;
}
