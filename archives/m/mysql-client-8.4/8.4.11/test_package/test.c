#include <mysql.h>
#include <stdio.h>
#include <string.h>

int main(void) {
  if (mysql_library_init(0, NULL, NULL)) {
    fprintf(stderr, "mysql_library_init failed\n");
    return 1;
  }
  printf("client info: %s\n", mysql_get_client_info());
  if (mysql_get_client_version() < 80411) {
    fprintf(stderr, "unexpected client version: %lu\n",
            (unsigned long)mysql_get_client_version());
    mysql_library_end();
    return 1;
  }
  if (!mysql_thread_safe()) {
    fprintf(stderr, "client library is not thread safe\n");
    mysql_library_end();
    return 1;
  }
  MYSQL *handle = mysql_init(NULL);
  if (!handle) {
    fprintf(stderr, "mysql_init failed\n");
    mysql_library_end();
    return 1;
  }
  printf("client version: %lu\n",
         (unsigned long)mysql_get_client_version());
  mysql_close(handle);
  mysql_library_end();
  printf("mysql-client-8.4 test OK\n");
  return 0;
}
