#include "uthash.h"
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

struct my_struct {
    int id;
    char name[10];
    UT_hash_handle hh;
};

int main(void)
{
    struct my_struct *users = NULL;
    struct my_struct *s;
    int i;
    char names[][10] = {"zero", "one", "two", "three", "four"};

    /* add 5 elements */
    for (i = 0; i < 5; i++) {
        s = (struct my_struct *)malloc(sizeof(struct my_struct));
        if (s == NULL) {
            fprintf(stderr, "FAIL: malloc failed\n");
            return 1;
        }
        s->id = i;
        strcpy(s->name, names[i]);
        HASH_ADD_INT(users, id, s);
    }

    /* count elements */
    int count = HASH_COUNT(users);
    if (count != 5) {
        fprintf(stderr, "FAIL: expected 5 elements, got %d\n", count);
        return 1;
    }

    /* find element with id=3 */
    int target = 3;
    HASH_FIND_INT(users, &target, s);
    if (s == NULL) {
        fprintf(stderr, "FAIL: element id=3 not found\n");
        return 1;
    }
    if (strcmp(s->name, "three") != 0) {
        fprintf(stderr, "FAIL: element id=3 name mismatch: %s\n", s->name);
        return 1;
    }

    /* delete element id=1 */
    int del_id = 1;
    HASH_FIND_INT(users, &del_id, s);
    if (s != NULL) {
        HASH_DEL(users, s);
        free(s);
    }
    count = HASH_COUNT(users);
    if (count != 4) {
        fprintf(stderr, "FAIL: expected 4 elements after delete, got %d\n", count);
        return 1;
    }

    /* cleanup */
    struct my_struct *current, *tmp;
    HASH_ITER(hh, users, current, tmp) {
        HASH_DEL(users, current);
        free(current);
    }

    printf("All uthash tests passed (add, count, find, delete, iterate)\n");
    return 0;
}
