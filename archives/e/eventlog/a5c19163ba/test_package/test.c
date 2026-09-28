#include <stdio.h>
#include <string.h>
#include <eventlog/evtlog.h>

int main(void) {
    /* 实际调用 libevtlog API：构造记录、添加 tag、格式化输出 */
    EVTCONTEXT *ctx = evt_ctx_init("test_eventlog", EVT_FAC_USER);
    if (!ctx) {
        fprintf(stderr, "evt_ctx_init failed\n");
        return 1;
    }

    EVTREC *rec = evt_rec_init(ctx, EVT_PRI_INFO | EVT_FAC_USER, "eventlog library test");
    if (!rec) {
        fprintf(stderr, "evt_rec_init failed\n");
        evt_ctx_free(ctx);
        return 1;
    }

    evt_rec_add_tag(rec, evt_tag_str("greeting", "hello"));
    evt_rec_add_tag(rec, evt_tag_int("answer", 42));

    char *formatted = evt_format(rec);
    if (!formatted) {
        fprintf(stderr, "evt_format failed\n");
        evt_rec_free(rec);
        evt_ctx_free(ctx);
        return 1;
    }

    /* 验证格式化输出确实包含注入的 tag 值 */
    int ok = (strstr(formatted, "greeting='hello'") != NULL) &&
             (strstr(formatted, "answer='42'") != NULL);
    printf("evt_format: %s\n", formatted);
    free(formatted);

    evt_rec_free(rec);
    evt_ctx_free(ctx);

    return ok ? 0 : 2;
}