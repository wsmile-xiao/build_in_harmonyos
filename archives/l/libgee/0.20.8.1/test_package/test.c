/* test.c — libgee 0.20.8 consumer smoke test (R34: 实质调用被测包 API)
 *
 * 创建 GeeArrayList（字符串列表），添加元素，校验集合大小，
 * 验证 libgee-0.8 的 C API（gee_collection_add / gee_collection_get_size）
 * 可编译、链接并正确运行。
 */
#include <gee.h>
#include <stdio.h>
#include <glib.h>

int main(void) {
    GeeArrayList *list = NULL;
    GeeCollection *col = NULL;
    gboolean ok;
    gint size;

    list = gee_array_list_new(G_TYPE_STRING,
                              (GBoxedCopyFunc) g_strdup,
                              (GDestroyNotify) g_free,
                              NULL, NULL, NULL);
    if (list == NULL) {
        fprintf(stderr, "FAIL: gee_array_list_new returned NULL\n");
        return 1;
    }
    col = GEE_COLLECTION(list);

    ok = gee_collection_add(col, "libgee");
    ok = gee_collection_add(col, "harmonyos") && ok;

    size = gee_collection_get_size(col);
    printf("libgee smoke test: size=%d\n", size);

    g_object_unref(list);
    return (ok && size == 2) ? 0 : 1;
}
