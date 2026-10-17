#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <mysql.h>

int main(void) {
    /* Compile-time guard: ensure the client headers really declare the API. */
    const char *client_version = mysql_get_client_info();
    if (client_version == NULL || client_version[0] == '\0') {
        fprintf(stderr, "FAIL: mysql_get_client_info() returned empty\n");
        return 1;
    }
    printf("libmariadb client version: %s\n", client_version);

    /* Real runtime link + API usage: must initialize and free a connection
     * object. If libmariadb is missing/broken, this fails at link or runtime. */
    MYSQL *mysql = mysql_init(NULL);
    if (mysql == NULL) {
        fprintf(stderr, "FAIL: mysql_init() returned NULL\n");
        return 1;
    }

    /* Without a live server the server-info accessor may return NULL, so we
     * only print it (no hard check) — the point of this test is to prove the
     * client library links and its public API is callable. */
    const char *server_info = mysql_get_server_info(mysql);
    if (server_info != NULL) {
        printf("mysql_get_server_info(): %s\n", server_info);
    } else {
        printf("mysql_get_server_info(): (not connected, NULL expected)\n");
    }

    mysql_close(mysql);
    printf("OK: libmariadb client linked and API callable\n");
    return 0;
}
