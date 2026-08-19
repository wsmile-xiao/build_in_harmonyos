#include <globus_common.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    globus_uuid_t uuid;
    /* GLOBUS_UUID_TEXTLEN is 36 characters; uuid.text adds one byte for NUL. */
    if (globus_uuid_create(&uuid) != 0 || strlen(uuid.text) != GLOBUS_UUID_TEXTLEN) {
        return 1;
    }
    if (globus_uuid_import(&uuid, "some-bogus-text") == GLOBUS_SUCCESS) {
        return 2;
    }

    globus_list_t *items = NULL;
    int first = 1;
    int second = 2;
    if (globus_list_insert(&items, &first) != 0) {
        return 3;
    }
    if (globus_list_insert(&items, &second) != 0 ||
        globus_list_size(items) != 2 ||
        *(int *) globus_list_first(items) != second) {
        globus_list_free(items);
        return 3;
    }
    globus_list_free(items);
    puts("globus-common UUID, list, and invalid-input checks passed");
    return 0;
}
