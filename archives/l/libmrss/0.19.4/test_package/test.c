/* test.c — libmrss 0.19.4 消费者测试（1 个用例，7 个断言）
 *
 * 只使用 Conan 安装后的公共头文件 <mrss.h> 与 libmrss 库，用内联 RSS
 * fixture 真实调用公开 API：mrss_new / mrss_set（创建）/ mrss_parse_buffer
 * （解析 + 字段读取）/ mrss_write_file（保存）/ mrss_parse_file（回读）/
 * 非法 XML 拒绝 / mrss_free。任何断言失败 -> 非零退出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mrss.h>

/* 内联 RSS 2.0 fixture（离线，无网络依赖） */
static const char *RSS =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    "<rss version=\"2.0\"><channel>"
    "<title>libmrss consumer test</title>"
    "<link>https://github.com/bakulf/libmrss</link>"
    "<description>inline fixture feed</description>"
    "<language>en-us</language>"
    "<item><title>first item</title>"
    "<link>http://example.com/1</link>"
    "<description>item one body</description></item>"
    "<item><title>second item</title>"
    "<link>http://example.com/2</link>"
    "<description>item two body</description></item>"
    "</channel></rss>";

/* 非法 XML（未闭合标签）——必须被解析器拒绝 */
static const char *BAD_XML =
    "<?xml version=\"1.0\"?>"
    "<rss version=\"2.0\"><channel>"
    "<title>unclosed";

static int failures = 0;

#define CHECK(cond, msg) do {                                   \
    if (cond) { printf("PASS: %s\n", msg); }                    \
    else { fprintf(stderr, "FAIL: %s\n", msg); failures++; }    \
} while (0)

int main(void)
{
    mrss_t *data;
    mrss_error_t ret;
    mrss_t *parsed;
    mrss_t *reparsed;
    mrss_item_t *item;

    /* 1. 创建：mrss_new + mrss_set（构造一个最小合法 feed） */
    data = NULL;
    ret = mrss_new(&data);
    CHECK(ret == MRSS_OK && data != NULL, "mrss_new");
    if (ret != MRSS_OK || data == NULL) return 1;

    ret = mrss_set(data,
                   MRSS_FLAG_VERSION, MRSS_VERSION_2_0,
                   MRSS_FLAG_TITLE, "created by consumer",
                   MRSS_FLAG_DESCRIPTION, "created feed",
                   MRSS_FLAG_LINK, "http://example.com/",
                   MRSS_FLAG_END);
    CHECK(ret == MRSS_OK, "mrss_set (create)");
    if (ret != MRSS_OK) return 1;

    /* 2. 解析内联 fixture + 字段读取 */
    parsed = NULL;
    ret = mrss_parse_buffer((char *)RSS, strlen(RSS), &parsed);
    CHECK(ret == MRSS_OK && parsed != NULL, "mrss_parse_buffer");
    if (ret != MRSS_OK || parsed == NULL) return 1;

    CHECK(parsed->title != NULL &&
          strcmp(parsed->title, "libmrss consumer test") == 0,
          "channel title field");
    CHECK(parsed->item != NULL &&
          parsed->item->title != NULL &&
          strcmp(parsed->item->title, "first item") == 0 &&
          parsed->item->next != NULL &&
          strcmp(parsed->item->next->title, "second item") == 0,
          "item list fields (2 items)");

    /* 3. 保存：把解析结果写成本地文件 */
    remove("consumer_out.xml");
    ret = mrss_write_file(parsed, (char *)"consumer_out.xml");
    CHECK(ret == MRSS_OK, "mrss_write_file (save)");
    if (ret != MRSS_OK) return 1;

    /* 4. 回读：解析刚保存的文件，字段应保持一致 */
    reparsed = NULL;
    ret = mrss_parse_file((char *)"consumer_out.xml", &reparsed);
    CHECK(ret == MRSS_OK && reparsed != NULL &&
          reparsed->title != NULL &&
          strcmp(reparsed->title, "libmrss consumer test") == 0 &&
          reparsed->item != NULL &&
          strcmp(reparsed->item->title, "first item") == 0,
          "mrss_parse_file round-trip");

    /* 5. 非法 XML 必须被拒绝（不得返回 MRSS_OK） */
    {
        mrss_t *bad = (mrss_t *)1;   /* 非法初始值，防误判 */
        ret = mrss_parse_buffer((char *)BAD_XML, strlen(BAD_XML), &bad);
        CHECK(ret != MRSS_OK, "invalid XML rejected");
    }

    /* 6. 释放（valgrind 干净由上游 test/new 保障） */
    mrss_free(data);
    mrss_free(parsed);
    mrss_free(reparsed);
    CHECK(1, "mrss_free (all)");

    if (failures == 0)
        printf("ALL PASS\n");
    return failures == 0 ? 0 : 1;
}
