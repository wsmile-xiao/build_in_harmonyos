/* test_package 消费者测试：实际调用 STC 5.0 库 API（头文件容器 + 链接 libstc.a） */
#include <stdio.h>
#include <string.h>

#include "stc/cstr.h"

#define i_type IVec,int
#define i_use_cmp
#include "stc/vec.h"

int main(void)
{
    int failed = 0;

    /* cstr：构造 + 追加 + 格式化（cstr_append_fmt 位于 libstc.a，验证静态库链接） */
    cstr s = cstr_lit("hello");
    cstr_append(&s, " world");
    cstr_append_fmt(&s, " %d", 2026);
    if (strcmp(cstr_str(&s), "hello world 2026") != 0) {
        printf("FAIL cstr content: %s\n", cstr_str(&s));
        failed = 1;
    }
    cstr_drop(&s);

    /* vec：模板容器（头文件实例化）push/at/size */
    IVec v = c_make(IVec, {1, 2, 3});
    IVec_push_back(&v, 4);
    if (IVec_size(&v) != 4 || *IVec_at(&v, 3) != 4) {
        printf("FAIL vec\n");
        failed = 1;
    }
    c_drop(IVec, &v);

    if (failed) {
        printf("test_stc: FAILED\n");
        return 1;
    }
    printf("test_stc: OK\n");
    return 0;
}
