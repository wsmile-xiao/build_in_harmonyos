#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <json-parser/json.h>

int main(void) {
    /* 实际调用被测库 json_parse API：解析合法 JSON 并校验结构 */
    const char *json_text = "{\"name\":\"json-parser\",\"version\":1}";
    json_value *value = json_parse(json_text, strlen(json_text));
    if (!value) {
        fprintf(stderr, "FAIL: json_parse returned NULL for valid JSON\n");
        return 1;
    }
    if (value->type != json_object) {
        fprintf(stderr, "FAIL: expected json_object, got type %d\n", value->type);
        json_value_free(value);
        return 1;
    }
    json_value_free(value);

    /* 非法 JSON 必须失败 */
    const char *bad_text = "{\"unterminated\":";
    json_value *bad = json_parse(bad_text, strlen(bad_text));
    if (bad) {
        fprintf(stderr, "FAIL: json_parse accepted invalid JSON\n");
        json_value_free(bad);
        return 1;
    }
    printf("test json-parser 1.1.0: OK (valid parse + invalid reject)\n");
    return 0;
}
