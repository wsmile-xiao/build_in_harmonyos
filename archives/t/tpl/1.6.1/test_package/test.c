#include <stdio.h>
#include "tpl.h"

/* 消费者视角实质测试：使用 tpl_map/tpl_pack/tpl_dump/tpl_load/tpl_unpack
   完整走一遍序列化-落盘-加载-反序列化闭环，验证包内库可正常链接与工作。 */
int main(void) {
    tpl_node *tn;
    int i, j = -1;

    tn = tpl_map("i", &i);
    if (tn == NULL) {
        printf("tpl_map failed\n");
        return 1;
    }
    i = 42;
    tpl_pack(tn, 0);
    tpl_dump(tn, TPL_FILE, "test_tpl.bin");
    tpl_free(tn);

    tn = tpl_map("i", &j);
    if (tn == NULL) {
        printf("tpl_map (load) failed\n");
        return 1;
    }
    if (tpl_load(tn, TPL_FILE, "test_tpl.bin") < 0) {
        printf("tpl_load failed\n");
        tpl_free(tn);
        return 1;
    }
    tpl_unpack(tn, 0);
    tpl_free(tn);

    if (j != 42) {
        printf("value mismatch: j=%d\n", j);
        return 1;
    }
    printf("test tpl 1.6.1: OK (roundtrip j=%d)\n", j);
    return 0;
}
