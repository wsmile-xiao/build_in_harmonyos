/* test_libplist.c — L1 test for libplist C API.
 *
 * Creates a plist dict, adds a boolean key, serializes to XML,
 * parses it back, and verifies the value matches.
 */
#include <plist/plist.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

int main(void) {
    /* Create a plist dict */
    plist_t dict = plist_new_dict();
    if (!dict) {
        fprintf(stderr, "FAIL: plist_new_dict returned NULL\n");
        return 1;
    }

    /* Add a boolean node */
    plist_t bool_node = plist_new_bool(1);
    if (!bool_node) {
        fprintf(stderr, "FAIL: plist_new_bool returned NULL\n");
        plist_free(dict);
        return 1;
    }
    plist_dict_set_item(dict, "test_key", bool_node);

    /* Serialize to XML */
    char *xml_data = NULL;
    uint32_t xml_size = 0;
    plist_to_xml(dict, &xml_data, &xml_size);
    if (!xml_data || xml_size == 0) {
        fprintf(stderr, "FAIL: plist_to_xml returned empty data\n");
        free(xml_data);
        plist_free(dict);
        return 1;
    }

    /* Verify XML contains expected content */
    if (strstr(xml_data, "test_key") == NULL) {
        fprintf(stderr, "FAIL: XML does not contain 'test_key'\n");
        free(xml_data);
        plist_free(dict);
        return 1;
    }

    /* Parse XML back */
    plist_t parsed = NULL;
    plist_from_xml(xml_data, xml_size, &parsed);
    if (!parsed) {
        fprintf(stderr, "FAIL: plist_from_xml returned NULL\n");
        free(xml_data);
        plist_free(dict);
        return 1;
    }

    /* Verify the parsed dict has our key */
    plist_t item = plist_dict_get_item(parsed, "test_key");
    if (!item) {
        fprintf(stderr, "FAIL: plist_dict_get_item returned NULL for 'test_key'\n");
        free(xml_data);
        plist_free(parsed);
        plist_free(dict);
        return 1;
    }

    /* Check it's a boolean with value 1 (true) */
    if (plist_get_node_type(item) != PLIST_BOOLEAN) {
        fprintf(stderr, "FAIL: expected PLIST_BOOLEAN type\n");
        free(xml_data);
        plist_free(parsed);
        plist_free(dict);
        return 1;
    }

    uint8_t bool_val = 0;
    plist_get_bool_val(item, &bool_val);
    if (bool_val != 1) {
        fprintf(stderr, "FAIL: expected bool value 1, got %d\n", bool_val);
        free(xml_data);
        plist_free(parsed);
        plist_free(dict);
        return 1;
    }

    printf("PASS: libplist C API test passed\n");
    free(xml_data);
    plist_free(parsed);
    plist_free(dict);
    return 0;
}
