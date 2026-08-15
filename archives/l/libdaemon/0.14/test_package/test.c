#include <stdio.h>
#include <syslog.h>
#include <libdaemon/daemon.h>

int main(void) {
    /* 调用 libdaemon 真实 API：daemon_log 写入 syslog */
    daemon_log(LOG_INFO, "test libdaemon 0.14: daemon_log API OK");
    printf("test libdaemon 0.14: OK\n");
    return 0;
}
