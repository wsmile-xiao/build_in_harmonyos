#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <readline/history.h>

int main(void)
{
    int failures = 0;

    /* Test 1: HS_HISTORY_VERSION — history.h version macro (readline 8.3 family) */
    if (HS_HISTORY_VERSION < 0x0803) {
        fprintf(stderr, "FAIL 1: HS_HISTORY_VERSION 0x%x older than 0x0803\n",
                HS_HISTORY_VERSION);
        failures++;
    } else {
        printf("PASS 1: HS_HISTORY_VERSION OK (0x%x)\n", HS_HISTORY_VERSION);
    }

    /* Test 2: using_history + fresh history state */
    using_history();
    if (history_length != 0) {
        fprintf(stderr, "FAIL 2: fresh history_length expected 0, got %d\n",
                history_length);
        failures++;
    } else {
        printf("PASS 2: using_history OK (history_length=0)\n");
    }

    /* Test 3: add_history + history_get round trip */
    add_history("first command");
    add_history("second command");
    HIST_ENTRY *entry = history_get(history_base);
    if (!entry || strcmp(entry->line, "first command") != 0) {
        fprintf(stderr, "FAIL 3: history_get returned wrong entry "
                "(expected 'first command', got '%s')\n",
                entry ? entry->line : "(null)");
        failures++;
    } else {
        printf("PASS 3: add_history + history_get OK\n");
    }

    /* Test 4: history_length after 2 insertions */
    if (history_length != 2) {
        fprintf(stderr, "FAIL 4: history_length expected 2, got %d\n",
                history_length);
        failures++;
    } else {
        printf("PASS 4: history_length = 2 OK\n");
    }

    /* Test 5: history_search substring match (direction 1 = forward) */
    int pos = history_search("second", 1);
    if (pos < 0) {
        fprintf(stderr, "FAIL 5: history_search(\"second\", 1) not found\n");
        failures++;
    } else {
        printf("PASS 5: history_search OK (pos=%d)\n", pos);
    }

    /* Test 6: history_set_pos + next_history traversal to 2nd entry
       (readline 8.3 history_set_pos returns 1 on success, 0 on failure) */
    if (history_set_pos(0) != 1) {
        fprintf(stderr, "FAIL 6: history_set_pos(0) failed\n");
        failures++;
    } else {
        HIST_ENTRY *second = next_history();
        if (!second || strcmp(second->line, "second command") != 0) {
            fprintf(stderr, "FAIL 6: next_history returned wrong entry "
                    "(expected 'second command', got '%s')\n",
                    second ? second->line : "(null)");
            failures++;
        } else {
            printf("PASS 6: history_set_pos + next_history OK\n");
        }
    }

    /* Test 7: remove_history + free_history_entry */
    HIST_ENTRY *removed = remove_history(0);
    if (!removed) {
        fprintf(stderr, "FAIL 7: remove_history(0) returned NULL\n");
        failures++;
    } else {
        char *data = free_history_entry(removed);
        free(data);
        if (history_length != 1) {
            fprintf(stderr, "FAIL 7: history_length after remove expected 1, got %d\n",
                    history_length);
            failures++;
        } else {
            printf("PASS 7: remove_history + free_history_entry OK\n");
        }
    }

    /* Test 8: history_total_bytes of remaining entry */
    int total = history_total_bytes();
    if (total <= 0) {
        fprintf(stderr, "FAIL 8: history_total_bytes expected > 0, got %d\n", total);
        failures++;
    } else {
        printf("PASS 8: history_total_bytes = %d OK\n", total);
    }

    /* Test 9: clear_history cleanup */
    clear_history();
    if (history_length != 0) {
        fprintf(stderr, "FAIL 9: clear_history failed, history_length=%d\n",
                history_length);
        failures++;
    } else {
        printf("PASS 9: clear_history OK (history_length=0)\n");
    }

    if (failures > 0) {
        fprintf(stderr, "\nlibhistory test FAILED: %d failure(s)\n", failures);
        return 1;
    }
    printf("\nlibhistory test PASSED\n");
    return 0;
}
