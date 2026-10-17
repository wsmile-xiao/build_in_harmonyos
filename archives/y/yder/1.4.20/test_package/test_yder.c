/* Consumer test for yder: exercise console and file logging backends.
 * Asserts init/log/close round-trips and that the file backend actually
 * writes the message to disk. */
#include <stdio.h>
#include <string.h>
#include <yder.h>

int main(void)
{
    const char *marker = "yder-consumer-test-marker";
    const char *log_file = "./yder_consumer_test.log";

    /* 1. console backend: init / log / close round-trip */
    if (!y_init_logs("yder_consumer_test", Y_LOG_MODE_CONSOLE,
                     Y_LOG_LEVEL_DEBUG, NULL, "consumer test")) {
        fprintf(stderr, "FAIL: console y_init_logs returned false\n");
        return 1;
    }
    y_log_message(Y_LOG_LEVEL_DEBUG, marker);
    y_close_logs();

    /* 2. file backend: the log file must exist and contain the marker */
    if (!y_init_logs("yder_consumer_test", Y_LOG_MODE_FILE,
                     Y_LOG_LEVEL_DEBUG, log_file, "consumer test file")) {
        fprintf(stderr, "FAIL: file y_init_logs returned false\n");
        return 1;
    }
    y_log_message(Y_LOG_LEVEL_INFO, marker);
    y_close_logs();

    {
        FILE *f = fopen(log_file, "r");
        char buf[512];
        int found = 0;
        if (!f) {
            fprintf(stderr, "FAIL: log file %s not created\n", log_file);
            return 1;
        }
        while (fgets(buf, sizeof(buf), f)) {
            if (strstr(buf, marker)) { found = 1; break; }
        }
        fclose(f);
        if (!found) {
            fprintf(stderr, "FAIL: marker not found in log file\n");
            return 1;
        }
    }

    /* 3. level constants keep their severity order (nibble masks, the
     * numeric value grows with severity) */
    if (!(Y_LOG_LEVEL_NONE < Y_LOG_LEVEL_ERROR &&
          Y_LOG_LEVEL_ERROR < Y_LOG_LEVEL_WARNING &&
          Y_LOG_LEVEL_WARNING < Y_LOG_LEVEL_INFO &&
          Y_LOG_LEVEL_INFO < Y_LOG_LEVEL_DEBUG)) {
        fprintf(stderr, "FAIL: level constant ordering changed\n");
        return 1;
    }

    /* 4. re-init after close works */
    if (!y_init_logs("yder_consumer_test2", Y_LOG_MODE_CONSOLE,
                     Y_LOG_LEVEL_INFO, NULL, "consumer test 2")) {
        fprintf(stderr, "FAIL: re-init after close returned false\n");
        return 1;
    }
    y_close_logs();

    printf("yder consumer test: PASS\n");
    return 0;
}
