#include <atk/atk.h>

int main(void) {
    if (atk_get_major_version() != 2) {
        return 1;
    }
    if (atk_get_minor_version() != 28) {
        return 2;
    }
    if (atk_get_micro_version() != 0) {
        return 3;
    }
    GType object_type = atk_object_get_type();
    GType relation_type = atk_relation_get_type();
    return (object_type == G_TYPE_INVALID || relation_type == G_TYPE_INVALID) ? 4 : 0;
}
