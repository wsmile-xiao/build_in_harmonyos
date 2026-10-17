/*
 * test_http_parser.c — http-parser 2.9.4 消费者测试 (test_package)
 *
 * 真实调用被测库 API（非 mock）：初始化解析器、注册回调、解析真实
 * HTTP 请求/响应、校验 method/url/header/body/status 等关键字段。
 * 任何断言失败 → 打印 FAIL 并返回非 0；全部通过 → 打印 PASS 并返回 0。
 */
#include <stdio.h>
#include <string.h>
#include "http_parser.h"

/* ---- 回调记录 ---- */
static int g_msg_begin = 0;
static int g_msg_complete = 0;
static int g_headers_complete = 0;
static int g_body_final = 0;      /* http_body_is_final() 在 body 回调内捕获 */
static char g_url[128] = {0};
static char g_header_field[64] = {0};
static char g_header_value[128] = {0};
static char g_body[128] = {0};
static size_t g_body_len = 0;

static void reset_records(void) {
    g_msg_begin = g_msg_complete = g_headers_complete = 0;
    g_body_final = 0;
    g_url[0] = g_header_field[0] = g_header_value[0] = g_body[0] = '\0';
    g_body_len = 0;
}

static int cb_message_begin(http_parser *p) { (void)p; g_msg_begin++; return 0; }
static int cb_url(http_parser *p, const char *at, size_t len) {
    (void)p; if (len < sizeof(g_url)) { memcpy(g_url, at, len); g_url[len] = '\0'; } return 0;
}
static int cb_header_field(http_parser *p, const char *at, size_t len) {
    (void)p; if (len < sizeof(g_header_field)) { memcpy(g_header_field, at, len); g_header_field[len] = '\0'; } return 0;
}
static int cb_header_value(http_parser *p, const char *at, size_t len) {
    (void)p; if (len < sizeof(g_header_value)) { memcpy(g_header_value, at, len); g_header_value[len] = '\0'; } return 0;
}
static int cb_headers_complete(http_parser *p) { (void)p; g_headers_complete++; return 0; }
/* body 回调可能被分多次调用（如 chunked），需累积拼接；
 * http_body_is_final() 只在 body 回调执行期间（s_message_done 状态）为真，
 * 与上游 test.c check_body_is_final() 的检查时机一致。 */
static int cb_body(http_parser *p, const char *at, size_t len) {
    if (g_body_len + len < sizeof(g_body)) {
        memcpy(g_body + g_body_len, at, len);
        g_body_len += len;
        g_body[g_body_len] = '\0';
    }
    if (http_body_is_final(p)) {
        g_body_final = 1;
    }
    return 0;
}
static int cb_message_complete(http_parser *p) { (void)p; g_msg_complete++; return 0; }

#define ASSERT(cond)                                                        \
    do {                                                                    \
        if (!(cond)) {                                                      \
            fprintf(stderr, "FAIL [%s:%d]: %s\n", __FILE__, __LINE__, #cond); \
            return 1;                                                       \
        }                                                                   \
    } while (0)

/* 1. 版本 */
static int test_version(void) {
    unsigned long v = http_parser_version();
    ASSERT(v == 0x020904UL);        /* 2.9.4 */
    ASSERT(((v >> 16) & 255) == 2);
    ASSERT(((v >> 8) & 255) == 9);
    ASSERT((v & 255) == 4);
    return 0;
}

/* 2. 请求解析: 方法/URL/Header/Body/回调 */
static int test_request(void) {
    const char *req =
        "POST /hello?q=1 HTTP/1.1\r\n"
        "Host: example.com\r\n"
        "Content-Length: 5\r\n"
        "\r\n"
        "hello";
    http_parser p;
    http_parser_settings s;

    reset_records();

    http_parser_init(&p, HTTP_REQUEST);
    http_parser_settings_init(&s);
    s.on_message_begin = cb_message_begin;
    s.on_url = cb_url;
    s.on_header_field = cb_header_field;
    s.on_header_value = cb_header_value;
    s.on_headers_complete = cb_headers_complete;
    s.on_body = cb_body;
    s.on_message_complete = cb_message_complete;

    size_t n = http_parser_execute(&p, &s, req, strlen(req));
    ASSERT(n == strlen(req));
    ASSERT(HTTP_PARSER_ERRNO(&p) == HPE_OK);
    ASSERT(p.http_major == 1 && p.http_minor == 1);
    ASSERT(p.method == HTTP_POST);
    ASSERT(strcmp(g_url, "/hello?q=1") == 0);
    ASSERT(strcmp(g_header_field, "Content-Length") == 0);
    ASSERT(strcmp(g_header_value, "5") == 0);
    ASSERT(strcmp(g_body, "hello") == 0);
    ASSERT(g_msg_begin == 1);
    ASSERT(g_headers_complete == 1);
    ASSERT(g_msg_complete == 1);
    ASSERT(http_should_keep_alive(&p) == 1);
    /* http_body_is_final 在最后一次 body 回调期间为真（与上游 check_body_is_final 一致） */
    ASSERT(g_body_final == 1);
    return 0;
}

/* 3. 响应解析: 状态码 */
static int test_response(void) {
    const char *res =
        "HTTP/1.1 404 Not Found\r\n"
        "Content-Type: text/html\r\n"
        "Content-Length: 0\r\n"
        "\r\n";
    http_parser p;
    http_parser_settings s;

    reset_records();

    http_parser_init(&p, HTTP_RESPONSE);
    http_parser_settings_init(&s);
    s.on_message_begin = cb_message_begin;
    s.on_headers_complete = cb_headers_complete;
    s.on_body = cb_body;
    s.on_message_complete = cb_message_complete;

    size_t n = http_parser_execute(&p, &s, res, strlen(res));
    ASSERT(n == strlen(res));
    ASSERT(HTTP_PARSER_ERRNO(&p) == HPE_OK);
    ASSERT(p.status_code == 404);
    ASSERT(p.http_major == 1 && p.http_minor == 1);
    ASSERT(g_msg_begin == 1);
    ASSERT(g_headers_complete == 1);
    ASSERT(g_msg_complete == 1);
    ASSERT(http_should_keep_alive(&p) == 1);
    return 0;
}

/* 4. 分块(chunked)解析: 跨多次 execute + 分块回调 */
static int test_chunked(void) {
    const char *hdr =
        "GET /chunk HTTP/1.1\r\n"
        "Transfer-Encoding: chunked\r\n"
        "\r\n";
    const char *body = "5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n";
    http_parser p;
    http_parser_settings s;

    reset_records();

    http_parser_init(&p, HTTP_REQUEST);
    http_parser_settings_init(&s);
    s.on_message_begin = cb_message_begin;
    s.on_url = cb_url;
    s.on_headers_complete = cb_headers_complete;
    s.on_body = cb_body;
    s.on_message_complete = cb_message_complete;

    size_t n = http_parser_execute(&p, &s, hdr, strlen(hdr));
    ASSERT(HTTP_PARSER_ERRNO(&p) == HPE_OK);
    ASSERT(n == strlen(hdr));
    ASSERT(g_msg_begin == 1);
    ASSERT(g_headers_complete == 1);
    ASSERT(strcmp(g_url, "/chunk") == 0);

    n = http_parser_execute(&p, &s, body, strlen(body));
    ASSERT(HTTP_PARSER_ERRNO(&p) == HPE_OK);
    ASSERT(n == strlen(body));
    ASSERT(strcmp(g_body, "hello world") == 0);
    ASSERT(g_msg_complete == 1);
    return 0;
}

/* 5. URL 解析: http_parser_parse_url 字段 */
static int test_parse_url(void) {
    const char *url = "http://user:pass@example.com:8080/path?q=1#frag";
    struct http_parser_url u;
    http_parser_url_init(&u);
    int rc = http_parser_parse_url(url, strlen(url), 0, &u);
    ASSERT(rc == 0);
    ASSERT((u.field_set & (1 << UF_SCHEMA)) != 0);
    ASSERT((u.field_set & (1 << UF_HOST)) != 0);
    ASSERT((u.field_set & (1 << UF_PORT)) != 0);
    ASSERT((u.field_set & (1 << UF_PATH)) != 0);
    ASSERT((u.field_set & (1 << UF_QUERY)) != 0);
    ASSERT((u.field_set & (1 << UF_FRAGMENT)) != 0);
    /* 逐字段比对内容 */
    ASSERT(strncmp(url + u.field_data[UF_SCHEMA].off, "http", u.field_data[UF_SCHEMA].len) == 0);
    ASSERT(strncmp(url + u.field_data[UF_HOST].off, "example.com", u.field_data[UF_HOST].len) == 0);
    ASSERT(strncmp(url + u.field_data[UF_PATH].off, "/path", u.field_data[UF_PATH].len) == 0);
    ASSERT(strncmp(url + u.field_data[UF_QUERY].off, "q=1", u.field_data[UF_QUERY].len) == 0);
    ASSERT(strncmp(url + u.field_data[UF_FRAGMENT].off, "frag", u.field_data[UF_FRAGMENT].len) == 0);
    ASSERT(u.port == 8080);
    return 0;
}

/* 6. 辅助 API: errno 名/描述、方法/状态字符串、keep-alive */
static int test_helpers(void) {
    ASSERT(strcmp(http_errno_name(HPE_OK), "HPE_OK") == 0);
    ASSERT(http_errno_description(HPE_INVALID_URL) != NULL);
    ASSERT(strcmp(http_method_str(HTTP_GET), "GET") == 0);
    ASSERT(strcmp(http_method_str(HTTP_POST), "POST") == 0);
    ASSERT(strcmp(http_status_str(200), "OK") == 0);
    ASSERT(http_errno_name(HPE_INVALID_EOF_STATE) != NULL);
    return 0;
}

int main(void) {
    int rc = 0;
    rc += test_version();
    rc += test_request();
    rc += test_response();
    rc += test_chunked();
    rc += test_parse_url();
    rc += test_helpers();
    if (rc != 0) {
        fprintf(stderr, "http-parser consumer test: %d group(s) FAILED\n", rc);
        return 1;
    }
    printf("http-parser consumer test: ALL PASS\n");
    return 0;
}
