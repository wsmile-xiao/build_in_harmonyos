#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/apparmor.h>

/* 消费者测试：实质调用 libapparmor 公开 API（R34）
 * aa_splitcon(char *con, char **mode) 返回 label 指针，指向 con 内部子串
 * （非 malloc，无需 free；mode 为 NULL 时返回 label）。验证库可链接可运行 */
int main(void) {
    char con[] = "unconfined";
    char *label = NULL;

    label = aa_splitcon(con, NULL);
    if (label == NULL || strcmp(label, "unconfined") != 0) {
        fprintf(stderr, "aa_splitcon label mismatch: got '%s'\n",
                label ? label : "(null)");
        return 1;
    }

    printf("libapparmor 5.0.0 consumer test: OK (label=%s)\n", label);
    return 0;
}
