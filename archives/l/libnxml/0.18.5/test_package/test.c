/* test.c — libnxml 0.18.5 消费者测试（1 个用例，多断言）
 *
 * 只使用 Conan 安装后的公共头文件 <nxml.h> 与 libnxml 库，真实调用
 * 公开 API：nxmle_new_data_from_buffer / nxmle_root_element /
 * nxmle_find_element / nxmle_find_attribute / nxml_write_buffer /
 * nxml_free。任何断言失败 -> 非零退出。
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <nxml.h>

static const char *XML =
    "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    "<library name=\"libnxml\">"
    "<book id=\"1\" lang=\"en\"><title>XML Parsing</title></book>"
    "<book id=\"2\" lang=\"zh\"><title>XML 解析</title></book>"
    "</library>";

int main(void)
{
    nxml_t *doc;
    nxml_data_t *root, *book, *title;
    nxml_error_t err;
    char *attr;
    char *buffer = NULL;

    /* 1. 从内存缓冲区解析 XML（size=0 表示按 NUL 结尾字符串处理） */
    doc = nxmle_new_data_from_buffer((char *)XML, 0, &err);
    if (doc == NULL) {
        fprintf(stderr, "FAIL: nxmle_new_data_from_buffer err=%d\n", err);
        return 1;
    }
    printf("PASS: nxmle_new_data_from_buffer\n");

    /* 2. 根元素解析与名字校验 */
    root = nxmle_root_element(doc, &err);
    if (root == NULL || strcmp(root->value, "library") != 0) {
        fprintf(stderr, "FAIL: root element (got %s, err=%d)\n",
                root ? root->value : "(null)", err);
        return 1;
    }
    printf("PASS: nxmle_root_element -> %s\n", root->value);

    /* 3. 根元素属性 */
    attr = nxmle_find_attribute(root, "name", &err);
    if (attr == NULL || strcmp(attr, "libnxml") != 0) {
        fprintf(stderr, "FAIL: root attr name (got %s)\n",
                attr ? attr : "(null)");
        return 1;
    }
    printf("PASS: nxmle_find_attribute(name) = %s\n", attr);

    /* 4. 子元素查找 + 嵌套文本（parent=root：在根的子级里找 book） */
    book = nxmle_find_element(doc, root, "book", &err);
    if (book == NULL) {
        fprintf(stderr, "FAIL: find first book (err=%d)\n", err);
        return 1;
    }
    attr = nxmle_find_attribute(book, "id", &err);
    if (attr == NULL || strcmp(attr, "1") != 0) {
        fprintf(stderr, "FAIL: book id (got %s)\n", attr ? attr : "(null)");
        return 1;
    }
    title = nxmle_find_element(doc, book, "title", &err);
    if (title == NULL || title->children == NULL ||
        title->children->type != NXML_TYPE_TEXT ||
        strcmp(title->children->value, "XML Parsing") != 0) {
        fprintf(stderr, "FAIL: title text\n");
        return 1;
    }
    printf("PASS: nested title text = '%s'\n", title->children->value);

    /* 5. 序列化回缓冲区（写出 API 往返；入参 buffer 必须为 NULL） */
    err = nxml_write_buffer(doc, &buffer);
    if (err != NXML_OK || buffer == NULL ||
        strstr(buffer, "library") == NULL ||
        strstr(buffer, "XML Parsing") == NULL) {
        fprintf(stderr, "FAIL: nxml_write_buffer (err=%d)\n", err);
        return 1;
    }
    printf("PASS: nxml_write_buffer (round-trip ok)\n");
    free(buffer);

    /* 6. 释放 */
    nxml_free(doc);
    printf("PASS: nxml_free\n");

    printf("ALL PASS\n");
    return 0;
}
