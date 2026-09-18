#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libubox/blob.h>
#include <libubox/blobmsg.h>
#include <libubox/blobmsg_json.h>

static int check(int cond, const char *msg)
{
    if (!cond) {
        printf("FAIL: %s\n", msg);
        return 1;
    }
    printf("OK: %s\n", msg);
    return 0;
}

int main(void)
{
    struct blob_buf buf = {0};
    struct blob_buf jbuf = {0};
    struct blob_attr *attr;
    unsigned int rem;
    int failed = 0;
    int found_name = 0;
    int found_year = 0;
    char *js = NULL;

    /* 1. blobmsg buffer init */
    failed |= check(blobmsg_buf_init(&buf) == 0, "blobmsg_buf_init");

    /* 2/3. add string + u32 fields */
    failed |= check(blobmsg_add_string(&buf, "name", "libblobmsg") == 0, "blobmsg_add_string");
    failed |= check(blobmsg_add_u32(&buf, "year", 2026) == 0, "blobmsg_add_u32");

    /* 4/5. iterate with blobmsg_for_each_attr and verify values */
    blobmsg_for_each_attr(attr, buf.head, rem) {
        if (strcmp(blobmsg_name(attr), "name") == 0) {
            found_name = 1;
            failed |= check(strcmp(blobmsg_get_string(attr), "libblobmsg") == 0, "blobmsg_get_string round-trip");
        } else if (strcmp(blobmsg_name(attr), "year") == 0) {
            found_year = 1;
            failed |= check(blobmsg_get_u32(attr) == 2026, "blobmsg_get_u32 round-trip");
        }
    }
    failed |= check(found_name && found_year, "both fields discovered");

    /* 6. typed parse with policy */
    {
        static const struct blobmsg_policy pol[] = {
            { .name = "name", .type = BLOBMSG_TYPE_STRING },
            { .name = "year", .type = BLOBMSG_TYPE_INT32 },
        };
        struct blob_attr *tb[2] = {0};
        int rc = blobmsg_parse(pol, 2, tb, blob_data(buf.head), blob_len(buf.head));
        failed |= check(rc == 0 && tb[0] && tb[1], "blobmsg_parse with policy");
    }

    /* 7. blobmsg -> JSON conversion is non-empty and carries fields */
    js = blobmsg_format_json(buf.head, false);
    failed |= check(js != NULL && js[0] != '\0', "blobmsg_format_json non-empty");
    if (js) {
        failed |= check(strstr(js, "libblobmsg") != NULL, "json contains name value");
        failed |= check(strstr(js, "2026") != NULL, "json contains year value");
        printf("json: %s\n", js);
        free(js);
        js = NULL;
    }

    /* 8. JSON string -> blobmsg */

    failed |= check(blobmsg_buf_init(&jbuf) == 0, "second blobmsg_buf_init");
    failed |= check(blobmsg_add_json_from_string(&jbuf, "{\"hello\": \"world\", \"n\": 7}"), "blobmsg_add_json_from_string");
    js = blobmsg_format_json(jbuf.head, false);
    failed |= check(js != NULL && strstr(js, "world") != NULL, "json parse round-trip");
    if (js) {
        printf("json2: %s\n", js);
        free(js);
    }

    blob_buf_free(&buf);
    blob_buf_free(&jbuf);
    printf("test libblobmsg API: %s\n", failed ? "FAIL" : "OK");
    return failed ? 1 : 0;
}
