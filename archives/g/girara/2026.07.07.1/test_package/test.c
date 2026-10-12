/* Consumer test for girara: standard header include + direct linking.
 * Simulates a real consumer application using the library's public API.
 */
#include <girara/datastructures.h>
#include <stdio.h>
#include <stddef.h>

int main(void) {
    girara_list_t *list = girara_list_new();
    if (!list) {
        fprintf(stderr, "FAIL: girara_list_new returned NULL\n");
        return 1;
    }
    printf("ok: girara_list_new\n");

    girara_list_append(list, (void *)0x1);
    girara_list_append(list, (void *)0x2);
    girara_list_append(list, (void *)0x3);
    if (girara_list_size(list) != 3) {
        fprintf(stderr, "FAIL: girara_list_size != 3\n");
        girara_list_free(list);
        return 1;
    }
    printf("ok: girara_list_size == 3 after 3 appends\n");

    if (girara_list_nth(list, 1) != (void *)0x2) {
        fprintf(stderr, "FAIL: girara_list_nth(1) mismatch\n");
        girara_list_free(list);
        return 1;
    }
    printf("ok: girara_list_nth(1) returns appended item\n");

    girara_list_free(list);
    printf("girara: consumer test passed (new/append/size/nth/free, 5 exported APIs)\n");
    return 0;
}
