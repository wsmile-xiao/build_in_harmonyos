/* test_package consumer test for c-algorithms 1.2.0 (libcalg).
 * Exercises real libcalg APIs: queue + list + slist + arraylist + hashtable.
 * R34: must genuinely depend on the tested package (no empty-string tests).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>

#include <libcalg.h>

/* HashTableEqualFunc-compatible wrapper for strcmp (void* signature). */
static int string_equals(void *a, void *b) {
    return strcmp((const char *) a, (const char *) b) == 0;
}

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
    assert(list_length(&head) == 3);
    assert(*(int *) list_nth_data(&head, 0) == 10);
    assert(*(int *) list_nth_data(&head, 2) == 30);
    list_free(head);

    /* SList: prepend + length */
    SListEntry *shead = NULL;
    slist_prepend(&shead, &x1);
    slist_prepend(&shead, &x2);
    assert(slist_length(shead) == 2);
    assert(*(int *) slist_data(shead) == 20);
    slist_free(shead);

    /* Arraylist: append + index */
    ArrayList *al = arraylist_new(4);
    assert(al != NULL);
    arraylist_append(al, &x1);
    arraylist_append(al, &x2);
    assert(arraylist_length(al) == 2);
    assert(*(int *) arraylist_get(al, 1) == 20);
    assert(arraylist_index_of(al, &x2) == 1);
    arraylist_free(al);

    /* HashTable: insert + lookup + remove */
    HashTable *ht = hash_table_new(string_hash, string_equals);
    assert(ht != NULL);
    assert(hash_table_insert(ht, "key", &x1));
    assert(*(int *) hash_table_lookup(ht, "key") == 10);
    assert(hash_table_remove(ht, "key") != 0);
    assert(hash_table_lookup(ht, "key") == NULL);
    hash_table_free(ht);

    printf("c-algorithms 1.2.0 consumer test OK\n");
    return 0;
}