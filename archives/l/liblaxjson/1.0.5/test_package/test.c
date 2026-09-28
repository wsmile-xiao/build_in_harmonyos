#include <laxjson.h>
#include <stdio.h>
#include <string.h>

/* Consumer-style test: parse a real JSON document with the library API. */
static int on_string(struct LaxJsonContext *context,
    enum LaxJsonType type, const char *value, int length)
{
    const char *type_name = type == LaxJsonTypeProperty ? "property" : "string";
    printf("%s: %s\n", type_name, value);
    return 0;
}

static int on_number(struct LaxJsonContext *context, double x)
{
    printf("number: %f\n", x);
    return 0;
}

static int on_primitive(struct LaxJsonContext *context, enum LaxJsonType type)
{
    const char *type_name;
    if (type == LaxJsonTypeTrue)
        type_name = "true";
    else if (type == LaxJsonTypeFalse)
        type_name = "false";
    else
        type_name = "null";
    printf("primitive: %s\n", type_name);
    return 0;
}

static int on_begin(struct LaxJsonContext *context, enum LaxJsonType type)
{
    const char *type_name = (type == LaxJsonTypeArray) ? "array" : "object";
    printf("begin %s\n", type_name);
    return 0;
}

static int on_end(struct LaxJsonContext *context, enum LaxJsonType type)
{
    const char *type_name = (type == LaxJsonTypeArray) ? "array" : "object";
    printf("end %s\n", type_name);
    return 0;
}

int main(void) {
    static const char *doc = "{\"hello\":\"world\",\"n\":42,\"flag\":true,\"list\":[1,2,3]}";
    struct LaxJsonContext *context;
    enum LaxJsonError err;
    size_t len = strlen(doc);

    context = lax_json_create();
    if (!context) {
        fprintf(stderr, "lax_json_create failed\n");
        return 1;
    }

    context->userdata = NULL;
    context->string = on_string;
    context->number = on_number;
    context->primitive = on_primitive;
    context->begin = on_begin;
    context->end = on_end;

    err = lax_json_feed(context, len, doc);
    if (err) {
        fprintf(stderr, "lax_json_feed error: %s\n", lax_json_str_err(err));
        lax_json_destroy(context);
        return 1;
    }
    err = lax_json_eof(context);
    if (err) {
        fprintf(stderr, "lax_json_eof error: %s\n", lax_json_str_err(err));
        lax_json_destroy(context);
        return 1;
    }
    lax_json_destroy(context);

    printf("test liblaxjson 1.0.5: OK\n");
    return 0;
}
