#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <axc/axc.h>

static int test_context(void)
{
    axc_context *ctx = 0;
    char db_fn[] = "test_axc.sqlite";
    char *got = 0;

    if (axc_context_create(&ctx) != 0 || ctx == 0) {
        printf("context_create failed\n");
        return 1;
    }
    if (axc_context_set_db_fn(ctx, db_fn, sizeof(db_fn)) != 0) {
        printf("set_db_fn failed\n");
        axc_context_destroy_all(ctx);
        return 1;
    }
    got = axc_context_get_db_fn(ctx);
    if (got == 0 || strcmp(got, db_fn) != 0) {
        printf("get_db_fn mismatch\n");
        axc_context_destroy_all(ctx);
        return 1;
    }
    if (axc_context_get_log_level(ctx) != -1) {
        printf("get_log_level default mismatch: %d\n", axc_context_get_log_level(ctx));
        axc_context_destroy_all(ctx);
        return 1;
    }
    axc_context_set_log_level(ctx, AXC_LOG_DEBUG);
    if (axc_context_get_log_level(ctx) != AXC_LOG_DEBUG) {
        printf("get_log_level round-trip failed\n");
        axc_context_destroy_all(ctx);
        return 1;
    }
    axc_context_destroy_all(ctx);
    printf("context test passed\n");
    return 0;
}

static int test_buf(void)
{
    const uint8_t raw[] = { 'a', 'x', 'c' };
    axc_buf *buf = axc_buf_create(raw, sizeof(raw));
    axc_buf_list_item *item = 0;
    uint32_t id = 7;

    if (buf == 0) {
        printf("buf_create failed\n");
        return 1;
    }
    if (axc_buf_get_len(buf) != sizeof(raw)) {
        printf("buf len mismatch\n");
        axc_buf_free(buf);
        return 1;
    }
    if (memcmp(axc_buf_get_data(buf), raw, sizeof(raw)) != 0) {
        printf("buf data mismatch\n");
        axc_buf_free(buf);
        return 1;
    }
    if (axc_buf_list_item_create(&item, &id, buf) != 0 || item == 0) {
        printf("list item create failed\n");
        axc_buf_free(buf);
        return 1;
    }
    if (axc_buf_list_item_get_id(item) != 7) {
        printf("list item id mismatch\n");
        axc_buf_list_free(item);
        return 1;
    }
    if (axc_buf_list_item_get_buf(item) != buf) {
        printf("list item buf mismatch\n");
        axc_buf_list_free(item);
        return 1;
    }
    axc_buf_list_free(item);
    printf("buf test passed\n");
    return 0;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        printf("usage: test_axc [context|buf]\n");
        return 2;
    }
    if (strcmp(argv[1], "context") == 0) {
        return test_context();
    }
    if (strcmp(argv[1], "buf") == 0) {
        return test_buf();
    }
    printf("unknown case: %s\n", argv[1]);
    return 2;
}
