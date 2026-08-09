#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <readline/readline.h>
#include <readline/history.h>

int main(void)
{
    int failures = 0;

    /* Test 1: rl_readline_version — verify we link against readline 8.3 */
    if (rl_readline_version < 0x0803) {
        fprintf(stderr, "FAIL 1: readline version 0x%x older than 0x0803\n",
                rl_readline_version);
        failures++;
    } else {
        printf("PASS 1: readline version OK (0x%x)\n", rl_readline_version);
    }

    /* Test 2: add_history + history_get — verify libhistory write+read */
    add_history("test command one");
    add_history("test command two");
    HIST_ENTRY *entry = history_get(1);
    if (!entry || strcmp(entry->line, "test command one") != 0) {
        fprintf(stderr, "FAIL 2: history_get returned wrong entry "
                "(expected 'test command one', got '%s')\n",
                entry ? entry->line : "(null)");
        failures++;
    } else {
        printf("PASS 2: add_history + history_get OK\n");
    }

    /* Test 3: history_length — verify count after 2 insertions */
    if (history_length != 2) {
        fprintf(stderr, "FAIL 3: history_length expected 2, got %d\n",
                history_length);
        failures++;
    } else {
        printf("PASS 3: history_length = %d OK\n", history_length);
    }

    /* Test 4: clear_history — verify cleanup */
    clear_history();
    if (history_length != 0) {
        fprintf(stderr, "FAIL 4: clear_history failed, history_length=%d\n",
                history_length);
        failures++;
    } else {
        printf("PASS 4: clear_history OK (history_length=0)\n");
    }

    if (failures > 0) {
        fprintf(stderr, "\nreadline test FAILED: %d failure(s)\n", failures);
        return 1;
    }
    printf("\nreadline test PASSED\n");
    return 0;
}
