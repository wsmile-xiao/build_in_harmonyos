/* test_package/test.c — ekhtml 消费者测试
   验证可链接 libekhtml 并解析一段 HTML（data 回调收集文本）。
*/
#include <ekhtml.h>
#include <stdio.h>
#include <string.h>

static int data_called = 0;

static void data_handler(void *cbdata, ekhtml_string_t *data) {
    if (data && data->str && data->len > 0) {
        data_called++;
    }
}

int main(void) {
    const char *html = "<html><body><p>Hello, OHOS!</p></body></html>";
    ekhtml_parser_t *parser = ekhtml_parser_new(NULL);
    if (!parser) {
        fprintf(stderr, "FAIL: ekhtml_parser_new failed\n");
        return 1;
    }

    ekhtml_parser_datacb_set(parser, data_handler);
    ekhtml_string_t input = { (char *)html, strlen(html) };
    ekhtml_parser_feed(parser, &input);
    ekhtml_parser_flush(parser, 1);

    if (data_called == 0) {
        fprintf(stderr, "FAIL: no data events (data_called=%d)\n", data_called);
        ekhtml_parser_destroy(parser);
        return 1;
    }

    ekhtml_parser_destroy(parser);
    printf("ekhtml smoke test: PASS (data events=%d)\n", data_called);
    return 0;
}
