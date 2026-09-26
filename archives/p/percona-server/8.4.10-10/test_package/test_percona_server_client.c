#include <mysql.h>
#include <stdio.h>

int main(void) {
    if (mysql_library_init(0, NULL, NULL) != 0) {
        return 1;
    }

    const char *info = mysql_get_client_info();
    unsigned long version = mysql_get_client_version();
    unsigned int thread_safe = mysql_thread_safe();
    mysql_library_end();

    if (info == NULL || info[0] == '\0' || version == 0) {
        return 2;
    }

    printf("percona-client:%s:%lu:%u\n", info, version, thread_safe);
    return 0;
}
