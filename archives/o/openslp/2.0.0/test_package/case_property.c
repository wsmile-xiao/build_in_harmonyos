#include <slp.h>
#include <string.h>

int main(void)
{
    const char *v;

    /* SLPSetProperty/SLPGetProperty contract: Set works as long as
     * SLPGetProperty has not been called first (per slp.h).  Set, then read. */
    SLPSetProperty("ohos.slp.test.prop", "val1");
    v = SLPGetProperty("ohos.slp.test.prop");
    if (v == 0 || strcmp(v, "val1") != 0) {
        return 1;
    }
    return 0;
}
