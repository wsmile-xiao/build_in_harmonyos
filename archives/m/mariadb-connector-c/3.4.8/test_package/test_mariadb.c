#include <stdio.h>
#include <mysql.h>

int main(void) {
    printf("MariaDB client library version: %s\n", mysql_get_client_info());
    MYSQL mysql;
    mysql_init(&mysql);
    mysql_close(&mysql);
    printf("mariadb-connector-c test passed\n");
    return 0;
}
