/* Stub implementations for libmysqlclient API on OHOS (no MySQL).
 * All functions return minimal values so mydumper compiles and links.
 * SPDX-License-Identifier: GPL-2.0-only */
#include <stdlib.h>

#include "mysql.h"

MYSQL *mysql_init(MYSQL *mysql) { (void) mysql; return NULL; }
MYSQL *mysql_real_connect(MYSQL *mysql, const char *host, const char *user,
                          const char *passwd, const char *db,
                          unsigned int port, const char *unix_socket,
                          unsigned long clientflag) {
    (void) mysql; (void) host; (void) user; (void) passwd; (void) db;
    (void) port; (void) unix_socket; (void) clientflag;
    return NULL;
}
void mysql_close(MYSQL *mysql) { (void) mysql; }
int mysql_ping(MYSQL *mysql) { (void) mysql; return 0; }
int mysql_query(MYSQL *mysql, const char *q) { (void) mysql; (void) q; return 0; }
int mysql_real_query(MYSQL *mysql, const char *q, unsigned long length) {
    (void) mysql; (void) q; (void) length;
    return 0;
}
MYSQL_RES *mysql_store_result(MYSQL *mysql) { (void) mysql; return NULL; }
MYSQL_RES *mysql_use_result(MYSQL *mysql) { (void) mysql; return NULL; }
void mysql_free_result(MYSQL_RES *result) { (void) result; }
MYSQL_ROW mysql_fetch_row(MYSQL_RES *result) { (void) result; return NULL; }
MYSQL_FIELD *mysql_fetch_fields(MYSQL_RES *result) { (void) result; return NULL; }
unsigned long *mysql_fetch_lengths(MYSQL_RES *result) { (void) result; return NULL; }
unsigned int mysql_num_fields(MYSQL_RES *result) { (void) result; return 0; }
my_ulonglong mysql_num_rows(MYSQL_RES *result) { (void) result; return 0; }
void mysql_data_seek(MYSQL_RES *result, my_ulonglong offset) {
    (void) result; (void) offset;
}
int mysql_next_result(MYSQL *mysql) { (void) mysql; return 0; }
int mysql_select_db(MYSQL *mysql, const char *db) { (void) mysql; (void) db; return 0; }
unsigned long mysql_real_escape_string(MYSQL *mysql, char *to,
                                       const char *from, unsigned long length) {
    (void) mysql; (void) to; (void) from; (void) length;
    return 0;
}
unsigned long mysql_hex_string(char *to, const char *from, unsigned long length) {
    (void) to; (void) from; (void) length;
    return 0;
}
const char *mysql_error(MYSQL *mysql) { (void) mysql; return "mysql stub"; }
unsigned int mysql_errno(MYSQL *mysql) { (void) mysql; return 0; }
const char *mysql_sqlstate(MYSQL *mysql) { (void) mysql; return "00000"; }
unsigned int mysql_warning_count(MYSQL *mysql) { (void) mysql; return 0; }
const char *mysql_character_set_name(MYSQL *mysql) { (void) mysql; return "utf8"; }
int mysql_set_character_set(MYSQL *mysql, const char *csname) {
    (void) mysql; (void) csname;
    return 0;
}
int mysql_options(MYSQL *mysql, int option, const void *arg) {
    (void) mysql; (void) option; (void) arg;
    return 0;
}
int mysql_options4(MYSQL *mysql, int option, const void *arg,
                   const void *arg2) {
    (void) mysql; (void) option; (void) arg; (void) arg2;
    return 0;
}
unsigned long mysql_get_server_version(MYSQL *mysql) { (void) mysql; return 0; }
unsigned long mysql_thread_id(MYSQL *mysql) { (void) mysql; return 0; }
my_ulonglong mysql_affected_rows(MYSQL *mysql) { (void) mysql; return 0; }
my_ulonglong mysql_insert_id(MYSQL *mysql) { (void) mysql; return 0; }
unsigned int mysql_field_count(MYSQL *mysql) { (void) mysql; return 0; }
int mysql_library_init(int argc, char **argv, char **groups) {
    (void) argc; (void) argv; (void) groups;
    return 0;
}
void mysql_library_end(void) { }
int mysql_thread_init(void) { return 0; }
void mysql_thread_end(void) { }
const char *mysql_get_client_info(void) { return "stub"; }
const char *mysql_get_host_info(MYSQL *mysql) { (void) mysql; return "stub"; }
const char *mysql_get_server_info(MYSQL *mysql) { (void) mysql; return "stub"; }
int mysql_ssl_set(MYSQL *mysql, const char *key, const char *cert,
                  const char *ca, const char *capath, const char *cipher) {
    (void) mysql; (void) key; (void) cert; (void) ca;
    (void) capath; (void) cipher;
    return 0;
}

char *getpass(const char *prompt) {
    (void) prompt;
    return NULL;
}
