#include <stdio.h>
#include <string.h>
#include <avro.h>

int main(void) {
    avro_schema_t schema;
    const char *json = "{\"type\": \"record\", \"name\": \"test\", \"fields\": []}";
    if (avro_schema_from_json_length(json, strlen(json), &schema)) {
        fprintf(stderr, "Failed to parse schema: %s\n", avro_strerror());
        return 1;
    }
    printf("Schema type: %s\n", avro_schema_type_name(schema));
    avro_schema_decref(schema);
    return 0;
}
