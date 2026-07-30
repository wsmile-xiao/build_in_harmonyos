#include <libisns/isns.h>
#include <libisns/attrs.h>
#include <string.h>

int main(void)
{
    isns_attr_list_t attrs;
    isns_portal_info_t portal;
    const char *entity = 0;

    if (strcmp(isns_strerror(ISNS_SUCCESS), "Success") != 0) {
        return 1;
    }
    if (!isns_portal_parse(&portal, "127.0.0.1:3205/tcp", 0)) {
        return 2;
    }

    isns_attr_list_init(&attrs);
    /* This API returns void; the lookup below verifies that insertion worked. */
    isns_attr_list_append_string(
        &attrs, ISNS_TAG_ENTITY_IDENTIFIER, "ohos.test.entity");
    if (!isns_attr_list_get_string(
            &attrs, ISNS_TAG_ENTITY_IDENTIFIER, &entity)) {
        isns_attr_list_destroy(&attrs);
        return 3;
    }
    if (entity == 0 || strcmp(entity, "ohos.test.entity") != 0) {
        isns_attr_list_destroy(&attrs);
        return 4;
    }
    isns_attr_list_destroy(&attrs);
    return 0;
}
