/* test_package consumer test for c-algorithms 1.0.0 (libcalg).
 * Exercises real libcalg APIs: queue + list + slist + arraylist + hashtable.
 * R34: must genuinely depend on the tested package (no empty-string tests).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <libcalg.h>

int main(void) {
    /* Queue: push head, pop head */
    Queue *queue = queue_new();
    assert(queue != NULL);
    assert(queue_is_empty(queue) != 0);
    int a = 1, b = 2, c = 3;
    queue_push_head(queue, &a);
    queue_push_head(queue, &b);
    queue_push_head(queue, &c);
    assert(queue_is_empty(queue) == 0);
    assert(*(int *) queue_pop_head(queue) == c);
    assert(*(int *) queue_pop_head(queue) == b);
    assert(*(int *) queue_pop_head(queue) == a);
    assert(queue_pop_head(queue) == NULL);
    queue_free(queue);

    /* List: append + length + nth data */
    ListEntry *head = NULL;
    int x1 = 10, x2 = 20, x3 = 30;
    list_append(&head, &x1);
    list_append(&head, &x2);
    list_append(&head, &x3);
    assert(list_length(head) == 3);
    assert(*(int *) list_nth_data(head, 0) == 10);
    assert(*(int *) list_nth_data(head, 2) == 30);
    list_free(head);

    /* Arraylist: append + index */
    ArrayList *al = arraylist_new(0);
    assert(al != NULL);
    arraylist_append(al, &x1);
    arraylist_append(al, &x2);
    assert(arraylist_length(al) == 2);
    assert(*(int *) arraylist_get(al, 1) == 20);
    arraylist_free(al);

    /* Hashtable: insert + lookup */
    HashTable *ht = hash_table_new(string_hash, string_equal);
    assert(ht != NULL);
    const char *key = "answer";
    int val = 42;
    hash_table_insert(ht, (void *) key, &val);
    assert(*(int *) hash_table_lookup(ht, (void *) key) == 42);
    hash_table_free(ht);

    printf("test c-algorithms 1.0.0: OK (queue/list/arraylist/hashtable)\n");
    return 0;
}
