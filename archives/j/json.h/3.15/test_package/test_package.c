/* test_package for json.h 3.15 — 消费者用例：真实解析 JSON 并断言结果。 */
#include <stdio.h>
#include <string.h>
#include "json.h"

int main(void) {
    const char *src = "{\"name\":\"json.h\",\"version\":3,\"ok\":true,\"tags\":[\"c\",\"c++\"]}";
    size_t src_size = strlen(src);
    struct json_value_s *root = json_parse(src, src_size);
    if (!root) {
        fprintf(stderr, "json_parse returned NULL\n");
        return 1;
    }
    if (root->type != json_type_object) {
        fprintf(stderr, "root is not an object\n");
        return 1;
    }
    /* 读取 "version" 字段并验证数值 3 */
    struct json_object_s *obj = (struct json_object_s *)root->payload;
    struct json_object_element_s *elt = obj->start;
    long found_version = -1;
    while (elt) {
        if (strcmp(elt->name->string, "version") == 0 &&
            elt->value->type == json_type_number) {
            struct json_number_s *num = (struct json_number_s *)elt->value->payload;
            found_version = strtol(num->number, NULL, 10);
        }
        elt = elt->next;
    }
    if (found_version != 3) {
        fprintf(stderr, "version mismatch: %ld\n", found_version);
        return 1;
    }
    free(root);
    printf("json.h consumer test passed: parsed object, version=%ld\n", found_version);
    return 0;
}
