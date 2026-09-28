#include <stdio.h>
#include "libdynamite.h"

/* 消费者视角验证：真实调用被测包 API（R34/PF3：禁止空壳测试）。
 * 空输入流必须返回错误而非成功，证明 dynamite_explode 已链接并执行。 */
static size_t empty_reader(void *buffer, size_t size, void *cookie) {
    (void)buffer; (void)size; (void)cookie;
    return 0;
}

static size_t sink_writer(void *buffer, size_t size, void *cookie) {
    (void)buffer; (void)size; (void)cookie;
    return size;
}

int main(void) {
    DynamiteResult r = dynamite_explode(empty_reader, sink_writer, NULL);
    printf("test dynamite 0.1.1: dynamite_explode(empty) -> %d\n", (int)r);
    /* 空流不得解出成功；返回 DYNAMITE_READ_ERROR(4) 即证明库正常工作 */
    if (r == DYNAMITE_SUCCESS) {
        fprintf(stderr, "FAIL: empty stream must not succeed\n");
        return 1;
    }
    printf("PASS: dynamite 0.1.1 consumer test OK\n");
    return 0;
}
