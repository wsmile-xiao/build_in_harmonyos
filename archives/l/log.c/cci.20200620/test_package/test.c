#include "log.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

static int callback_count;
static char callback_message[64];

static void capture_callback(log_Event *event) {
    callback_count++;
    vsnprintf(callback_message, sizeof(callback_message), event->fmt, event->ap);
}

int main(void) {
    if (strcmp(LOG_VERSION, "0.1.0") != 0) {
        return 1;
    }
    if (strcmp(log_level_string(LOG_WARN), "WARN") != 0) {
        return 2;
    }

    log_set_quiet(true);
    log_set_level(LOG_INFO);
    if (log_add_callback(capture_callback, NULL, LOG_WARN) != 0) {
        return 3;
    }

    log_info("ignored %d", 1);
    log_warn("captured %d", 42);
    if (callback_count != 1 || strcmp(callback_message, "captured 42") != 0) {
        return 4;
    }

    puts("log.c consumer test passed");
    return 0;
}
