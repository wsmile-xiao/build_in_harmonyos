#include <stdio.h>

#include <cattle/cattle.h>

int main(void) {
    CattleInterpreter *interpreter;

    /* 调用 cattle 公开 API：创建 Brainfuck 解释器并释放 */
    interpreter = cattle_interpreter_new();
    if (interpreter == NULL) {
        fprintf(stderr, "FAIL: cattle_interpreter_new returned NULL\n");
        return 1;
    }

    g_object_unref(interpreter);
    printf("PASS: cattle_interpreter_new ok\n");
    return 0;
}
