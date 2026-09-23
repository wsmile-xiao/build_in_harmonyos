/* test.c — libfastjson consumer test: JSON parse/print round-trip (R34: real API).

Uses libfastjson public API to:
  1. parse a JSON object string
  2. verify typed accessors (string/int/double/bool)
  3. serialize back to string and compare
  4. create a new object programmatically, then re-parse it (round-trip #2)
*/
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "libfastjson/json.h"
#include "libfastjson/json_object.h"
#include "libfastjson/json_tokener.h"
#include "libfastjson/json_util.h"

static int failures = 0;

#define CHECK(cond, msg) do { \
    if (!(cond)) { fprintf(stderr, "FAIL: %s\n", msg); failures++; } \
} while (0)

int main(void) {
    printf("libfastjson version: %s\n", fjson_version());

    /* --- 1. parse a JSON object --- */
    const char *src = "{\"name\":\"libfastjson\",\"port\":514,\"pi\":3.14,\"ohos\":true}";
    fjson_object *root = fjson_tokener_parse(src);
    CHECK(root != NULL, "fjson_tokener_parse returned NULL");
    if (!root) { return 1; }

    /* --- 2. typed accessors --- */
    fjson_object *o;
    CHECK(fjson_object_object_get_ex(root, "name", &o) && fjson_object_is_type(o, fjson_type_string),
          "field 'name' missing or not a string");
    if (o) CHECK(strcmp(fjson_object_get_string(o), "libfastjson") == 0, "name != 'libfastjson'");

    CHECK(fjson_object_object_get_ex(root, "port", &o) && fjson_object_is_type(o, fjson_type_int),
          "field 'port' missing or not an int");
    if (o) CHECK(fjson_object_get_int(o) == 514, "port != 514");

    CHECK(fjson_object_object_get_ex(root, "pi", &o) && fjson_object_is_type(o, fjson_type_double),
          "field 'pi' missing or not a double");
    if (o) CHECK(fjson_object_get_double(o) > 3.13 && fjson_object_get_double(o) < 3.15, "pi != 3.14");

    CHECK(fjson_object_object_get_ex(root, "ohos", &o) && fjson_object_is_type(o, fjson_type_boolean),
          "field 'ohos' missing or not a boolean");
    if (o) CHECK(fjson_object_get_boolean(o) == 1, "ohos != true");

    /* --- 3. serialize back and re-parse (round-trip) --- */
    const char *dump = fjson_object_to_json_string(root);
    CHECK(dump != NULL, "fjson_object_to_json_string returned NULL");
    fjson_object *re = fjson_tokener_parse(dump);
    CHECK(re != NULL, "re-parse of serialized output failed");
    if (re) {
        CHECK(fjson_object_object_get_ex(re, "port", &o) && fjson_object_get_int(o) == 514,
              "round-trip: port mismatch");
        fjson_object_put(re);
    }

    /* --- 4. programmatic object -> serialize -> parse (round-trip #2) --- */
    fjson_object *obj = fjson_object_new_object();
    fjson_object *str = fjson_object_new_string("harmony");
    fjson_object_object_add(obj, "os", str);
    fjson_object *arr = fjson_object_new_array();
    fjson_object_array_add(arr, fjson_object_new_int(2609));
    fjson_object_object_add(obj, "version", arr);
    const char *out2 = fjson_object_to_json_string(obj);
    CHECK(out2 != NULL && strstr(out2, "harmony") != NULL && strstr(out2, "2609") != NULL,
          "programmatic object serialization missing fields");
    fjson_object *re2 = fjson_tokener_parse(out2);
    CHECK(re2 != NULL, "re-parse of programmatic object failed");
    if (re2) {
        CHECK(fjson_object_object_get_ex(re2, "os", &o) &&
              strcmp(fjson_object_get_string(o), "harmony") == 0,
              "round-trip #2: os field mismatch");
        fjson_object_put(re2);
    }
    fjson_object_put(obj);
    fjson_object_put(root);

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("test libfastjson 1.2609.0: OK (parse + typed access + round-trip)\n");
    return 0;
}
