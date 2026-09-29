#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int run_command_capture(const char *cmd, char *outbuf, size_t outsz) {
    FILE *fp = popen(cmd, "r");
    if (!fp) {
        return -1;
    }
    size_t total = 0;
    outbuf[0] = '\0';
    while (total + 1 < outsz && fgets(outbuf + total, (int)(outsz - total), fp) != NULL) {
        total = strlen(outbuf);
        if (total >= outsz - 1) {
            break;
        }
    }
    int rc = pclose(fp);
    if (rc != 0) {
        return -1;
    }
    if (total == 0) {
        return -1;
    }
    return 0;
}

int main(void) {
    char output[8192] = {0};
    int ok = 0;
    const char *validated_via = NULL;

#ifdef ASTERISK_BIN
    {
        char cmd[1024];
        /* ASTERISK_BIN is injected by CMake as quoted string */
        snprintf(cmd, sizeof(cmd), "\"%s\" -V 2>&1", ASTERISK_BIN);
        printf("[test] trying ASTERISK_BIN=\"%s\" -V ...\n", ASTERISK_BIN);
        memset(output, 0, sizeof(output));
        if (run_command_capture(cmd, output, sizeof(output)) == 0) {
            printf("[test] output via ASTERISK_BIN: %s\n", output);
            if (strstr(output, "Asterisk") != NULL && strstr(output, "22.10.1") != NULL) {
                printf("[test] Asterisk version verified via ASTERISK_BIN\n");
                ok = 1;
                validated_via = ASTERISK_BIN;
            } else {
                printf("[test] output missing required strings ('Asterisk' and '22.10.1') via ASTERISK_BIN\n");
            }
        } else {
            printf("[test] ASTERISK_BIN execution failed (non-zero or no output), fallback to PATH search\n");
            if (output[0] != '\0') {
                printf("[test] last output: %s\n", output);
            }
        }
    }
#endif

    if (!ok) {
        const char *candidates[] = {
            "asterisk -V 2>&1",
            "sbin/asterisk -V 2>&1",
            NULL
        };
        for (int i = 0; candidates[i] != NULL; i++) {
            printf("[test] trying fallback candidate: %s ...\n", candidates[i]);
            memset(output, 0, sizeof(output));
            if (run_command_capture(candidates[i], output, sizeof(output)) == 0) {
                printf("[test] output via '%s': %s\n", candidates[i], output);
                if (strstr(output, "Asterisk") != NULL && strstr(output, "22.10.1") != NULL) {
                    printf("[test] Asterisk version verified via fallback '%s'\n", candidates[i]);
                    ok = 1;
                    validated_via = candidates[i];
                    break;
                } else {
                    printf("[test] candidate '%s' output missing required strings\n", candidates[i]);
                }
            } else {
                printf("[test] candidate '%s' failed to execute or returned non-zero\n", candidates[i]);
                if (output[0] != '\0') {
                    printf("[test] last output: %s\n", output);
                }
            }
        }
    }

    if (ok) {
        printf("[test] PASS: asterisk binary validated via '%s' — output contains 'Asterisk' and '22.10.1'\n",
               validated_via ? validated_via : "unknown");
        printf("[test] final captured output: %s\n", output);
        return 0;
    } else {
        fprintf(stderr, "[test] FAIL: unable to validate asterisk -V (requires exit 0 and output containing 'Asterisk' and '22.10.1')\n");
        if (output[0] != '\0') {
            fprintf(stderr, "[test] last captured output: %s\n", output);
        } else {
            fprintf(stderr, "[test] no output captured from any candidate\n");
        }
        return 1;
    }
}
