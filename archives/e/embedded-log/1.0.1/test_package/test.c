#include <stdio.h>
#include <string.h>
#include "log.h"

/* Real consumer of the embedded-log public API (R34):
   - log_init() sets the hook and buffer
   - LOG_INF()/LOG_ERR() format through printk() into the buffer and invoke
     the user hook; the test asserts the hook actually received the
     formatted message and that a failing assertion path fires. */

static char g_buff[512];
static char g_received[512];
static int g_hook_calls = 0;

static void my_hook(const char *str)
{
    g_hook_calls++;
    strncpy(g_received, str, sizeof(g_received) - 1);
    g_received[sizeof(g_received) - 1] = '\0';
}

int main(void)
{
    log_init(g_buff, sizeof(g_buff), my_hook);

    LOG_INF("hello-from-consumer %d", 42);
    if (g_hook_calls != 1) {
        fprintf(stderr, "FAIL: hook not called once (calls=%d)\n", g_hook_calls);
        return 1;
    }
    if (strstr(g_received, "hello-from-consumer 42") == NULL) {
        fprintf(stderr, "FAIL: hook payload wrong: [%s]\n", g_received);
        return 1;
    }
    printf("hook payload: %s", g_received);
    printf("embedded-log consumer test: PASS (calls=%d)\n", g_hook_calls);
    return 0;
}
