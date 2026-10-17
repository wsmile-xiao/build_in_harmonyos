#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <avro.h>

int main(void) {
    int rval;
    const char *json_schema =
        "{"
        "  \"type\": \"record\","
        "  \"name\": \"test\","
        "  \"fields\": ["
        "    { \"name\": \"name\", \"type\": \"string\" },"
        "    { \"name\": \"age\", \"type\": \"int\" }"
        "  ]"
        "}";

    /* Parse schema from JSON */
    avro_schema_t schema = NULL;
    avro_schema_error_t error;
    rval = avro_schema_from_json(json_schema, strlen(json_schema), &schema, &error);
    if (rval != 0) {
        fprintf(stderr, "Failed to parse schema: %s\n", avro_strerror());
        return 1;
    }
    printf("Schema parsed successfully\n");

    /* Verify schema copy and equality */
    avro_schema_t schema_copy = avro_schema_copy(schema);
    if (!avro_schema_equal(schema, schema_copy)) {
        fprintf(stderr, "Schema copy/equality failed\n");
        avro_schema_decref(schema_copy);
        avro_schema_decref(schema);
        return 1;
    }
    avro_schema_decref(schema_copy);
    printf("Schema copy/equality verified\n");

    /* Create a record datum */
    avro_datum_t record = avro_record(schema);
    if (record == NULL) {
        fprintf(stderr, "Failed to create record datum\n");
        avro_schema_decref(schema);
        return 1;
    }

    /* Set fields */
    avro_datum_t name_datum = avro_string("AvroTest");
    avro_datum_t age_datum = avro_int32(42);
    rval = avro_record_set(record, "name", name_datum);
    if (rval != 0) {
        fprintf(stderr, "Failed to set name field\n");
        avro_datum_decref(record);
        avro_schema_decref(schema);
        return 1;
    }
    rval = avro_record_set(record, "age", age_datum);
    if (rval != 0) {
        fprintf(stderr, "Failed to set age field\n");
        avro_datum_decref(record);
        avro_schema_decref(schema);
        return 1;
    }

    /* Read back and verify name field */
    avro_datum_t read_name = NULL;
    rval = avro_record_get(record, "name", &read_name);
    if (rval != 0 || !is_avro_string(read_name)) {
        fprintf(stderr, "Failed to get name field\n");
        avro_datum_decref(record);
        avro_schema_decref(schema);
        return 1;
    }
    char *name_str = NULL;
    rval = avro_string_get(read_name, &name_str);
    if (rval != 0 || strcmp(name_str, "AvroTest") != 0) {
        fprintf(stderr, "Name value mismatch: got %s\n", name_str ? name_str : "(null)");
        avro_datum_decref(record);
        avro_schema_decref(schema);
        return 1;
    }
    printf("Name field verified: %s\n", name_str);

    /* Read back and verify age field */
    avro_datum_t read_age = NULL;
    rval = avro_record_get(record, "age", &read_age);
    if (rval != 0 || !is_avro_int32(read_age)) {
        fprintf(stderr, "Failed to get age field\n");
        avro_datum_decref(record);
        avro_schema_decref(schema);
        return 1;
    }
    int32_t age_val = 0;
    rval = avro_int32_get(read_age, &age_val);
    if (rval != 0 || age_val != 42) {
        fprintf(stderr, "Age value mismatch: got %d\n", age_val);
        avro_datum_decref(record);
        avro_schema_decref(schema);
        return 1;
    }
    printf("Age field verified: %d\n", age_val);

    /* Cleanup */
    avro_datum_decref(record);
    avro_schema_decref(schema);

    printf("avro-c 1.12.0 test passed\n");
    return 0;
}
