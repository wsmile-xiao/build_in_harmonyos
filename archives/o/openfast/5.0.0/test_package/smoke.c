#include <stdio.h>
#include <string.h>
#include "FAST_Library.h"

/*
 * OpenFAST 库级冒烟（消费者视角）：加载 openfastlib，走通
 * FAST_AllocateTurbines（分配涡轮机数据）→ FAST_DeallocateTurbines（释放）全链路。
 *
 * 注意 API 语义：FAST_AllocateTurbines 的第一个参数是 INTENT(IN) 的**涡轮机数量**
 * （FAST_Library.h: `void FAST_AllocateTurbines(int *iTurb, int *ErrStat, char *ErrMsg)`，
 *  F90 侧 `INTEGER(C_INT), INTENT(IN) :: nTurbines`），不是返回值，故断言只能落在
 * ErrStat 与 ErrMsg（NUL 结尾）上。
 */
int main(void)
{
    int nTurbines = 2;
    int ErrStat = -1;
    char ErrMsg[1025];
    size_t len;

    memset(ErrMsg, '?', sizeof(ErrMsg));

    FAST_AllocateTurbines(&nTurbines, &ErrStat, ErrMsg);
    printf("FAST_AllocateTurbines(n=%d) -> ErrStat=%d ErrMsg=\"%s\"\n", nTurbines, ErrStat, ErrMsg);
    if (ErrStat != 0) {
        fprintf(stderr, "FAIL: FAST_AllocateTurbines ErrStat=%d\n", ErrStat);
        return 1;
    }
    len = strnlen(ErrMsg, sizeof(ErrMsg));
    if (len >= sizeof(ErrMsg)) {
        fprintf(stderr, "FAIL: ErrMsg is not NUL-terminated within %zu bytes\n", sizeof(ErrMsg));
        return 1;
    }

    FAST_DeallocateTurbines(&ErrStat, ErrMsg);
    printf("FAST_DeallocateTurbines -> ErrStat=%d ErrMsg=\"%s\"\n", ErrStat, ErrMsg);
    if (ErrStat != 0) {
        fprintf(stderr, "FAIL: FAST_DeallocateTurbines ErrStat=%d\n", ErrStat);
        return 1;
    }

    printf("OpenFAST library smoke test PASSED (3 assertions)\n");
    return 0;
}
