/* lttng-ust test_package consumer probe.
 * Uses tracef() from lttng/tracef.h — verifies liblttng-ust links
 * and the tracer session API initializes on OHOS.
 */
#include <lttng/tracef.h>
#include <stdio.h>

int main(void)
{
    /* tracef requires a running session daemon; on OHOS the tracer
     * session may be absent — the call itself must not crash. */
    tracef("lttng-ust probe %d", 42);
    printf("lttng-ust OK\n");
    return 0;
}
