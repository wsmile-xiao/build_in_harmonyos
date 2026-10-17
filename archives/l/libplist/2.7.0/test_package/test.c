#include <plist/plist.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    plist_t dict = plist_new_dict();
    plist_t bool_node;
    char *xml_data = NULL;
    uint32_t xml_size = 0;
    plist_t parsed = NULL;
    plist_t item;
    uint8_t bool_val = 0;

    if (!dict) {
        fprintf(stderr, "FAIL: plist_new_dict returned NULL\n");
        return 1;
    }
    bool_node = plist_new_bool(1);
    if (!bool_node) {
        plist_free(dict);
        fprintf(stderr, "FAIL: plist_new_bool returned NULL\n");
        return 1;
    }
    plist_dict_set_item(dict, "test_key", bool_node);

    if (plist_to_xml(dict, &xml_data, &xml_size) != PLIST_ERR_SUCCESS
        || !xml_data || xml_size == 0) {
        plist_free(dict);
        free(xml_data);
        fprintf(stderr, "FAIL: plist_to_xml returned empty data\n");
        return 1;
    }
    if (!strstr(xml_data, "test_key")) {
        free(xml_data);
        plist_free(dict);
        fprintf(stderr, "FAIL: XML does not contain test_key\n");
        return 1;
    }
    if (plist_from_xml(xml_data, xml_size, &parsed) != PLIST_ERR_SUCCESS || !parsed) {
        free(xml_data);
        plist_free(dict);
        fprintf(stderr, "FAIL: plist_from_xml returned NULL\n");
        return 1;
    }

    item = plist_dict_get_item(parsed, "test_key");
    if (!item || plist_get_node_type(item) != PLIST_BOOLEAN) {
        free(xml_data);
        plist_free(parsed);
        plist_free(dict);
        fprintf(stderr, "FAIL: parsed test_key is not a boolean\n");
        return 1;
    }
    plist_get_bool_val(item, &bool_val);
    if (bool_val != 1) {
        free(xml_data);
        plist_free(parsed);
        plist_free(dict);
        fprintf(stderr, "FAIL: parsed boolean value is not true\n");
        return 1;
    }

    free(xml_data);
    plist_free(parsed);
    plist_free(dict);
    printf("PASS: libplist C XML round-trip test\n");
    return 0;
}
