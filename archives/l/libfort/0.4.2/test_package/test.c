#include <stdio.h>
#include <string.h>
#include <fort.h>

int main(void) {
    /* libfort 真实 API 冒烟：创建表格、写入单元格、取字符串、销毁 */
    ft_table_t *table = ft_create_table();
    if (table == NULL) {
        fprintf(stderr, "ft_create_table failed\n");
        return 1;
    }

    int rc = ft_write_ln(table, "libfort", "0.4.2", "smoke");
    if (rc != 0) {
        fprintf(stderr, "ft_write_ln failed rc=%d\n", rc);
        ft_destroy_table(table);
        return 1;
    }

    const char *out = ft_to_string(table);
    if (out == NULL) {
        fprintf(stderr, "ft_to_string returned NULL\n");
        ft_destroy_table(table);
        return 1;
    }

    /* 断言：输出包含写入的单元格文本 */
    if (strstr(out, "libfort") == NULL || strstr(out, "0.4.2") == NULL) {
        fprintf(stderr, "output missing expected cells:\n%s\n", out);
        ft_destroy_table(table);
        return 1;
    }

    printf("%s", out);
    printf("test libfort 0.4.2: OK (real API table round-trip)\n");
    ft_destroy_table(table);
    return 0;
}