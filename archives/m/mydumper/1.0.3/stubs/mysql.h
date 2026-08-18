/* Minimal stub of mysql.h (libmysqlclient) for OHOS (no MySQL).
 * Types/constants/functions used by mydumper; implementations in
 * stub-mysql.c (return 0/NULL). SPDX-License-Identifier: GPL-2.0-only */
#ifndef MYSQL_STUB_H
#define MYSQL_STUB_H

#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

typedef uint64_t my_ulonglong;
typedef struct MYSQL MYSQL;
typedef struct MYSQL_RES MYSQL_RES;
typedef char **MYSQL_ROW;
typedef unsigned int MYSQL_FIELD_OFFSET;

struct MYSQL {
    int dummy;
};

struct MYSQL_RES {
    int dummy;
};

typedef struct MYSQL_FIELD {
    char *name;
    char *org_name;
    char *table;
    char *org_table;
    char *db;
    char *catalog;
    char *def;
    unsigned long length;
    unsigned long max_length;
    unsigned int name_length;
    unsigned int org_name_length;
    unsigned int table_length;
    unsigned int org_table_length;
    unsigned int db_length;
    unsigned int catalog_length;
    unsigned int def_length;
    unsigned int flags;
    unsigned int decimals;
    unsigned int charsetnr;
    unsigned char type;
} MYSQL_FIELD;

#define CLIENT_VERSION 0
#define MYSQL_SERVER_VERSION "1.0.3-stub"
#define MYSQL_VERSION_ID 0
#define MYSQL_PORT 3306
#define MYSQL_READ_DEFAULT_FILE 0x8000L
#define MYSQL_READ_DEFAULT_GROUP 0x2000L

enum mysql_protocol_type {
    MYSQL_PROTOCOL_DEFAULT,
    MYSQL_PROTOCOL_TCP,
    MYSQL_PROTOCOL_SOCKET,
    MYSQL_PROTOCOL_PIPE,
    MYSQL_PROTOCOL_MEMORY
};

enum mysql_option {
    MYSQL_OPT_CONNECT_TIMEOUT,
    MYSQL_OPT_COMPRESS,
    MYSQL_OPT_NAMED_PIPE,
    MYSQL_OPT_PROTOCOL,
    MYSQL_OPT_READ_TIMEOUT,
    MYSQL_OPT_WRITE_TIMEOUT,
    MYSQL_OPT_LOCAL_INFILE,
    MYSQL_OPT_SSL_VERIFY_SERVER_CERT,
    MYSQL_OPT_SSL_KEY,
    MYSQL_OPT_SSL_CERT,
    MYSQL_OPT_SSL_CA,
    MYSQL_OPT_SSL_CAPATH,
    MYSQL_OPT_SSL_CIPHER,
    MYSQL_OPT_SSL_MODE,
    MYSQL_OPT_SSL_ENFORCE,
    MYSQL_OPT_TLS_VERSION,
    MYSQL_OPT_CONNECT_ATTR_ADD,
    MYSQL_OPT_CONNECT_ATTR_DELETE,
    MYSQL_ENABLE_CLEARTEXT_PLUGIN
};

/* enum_field_types（mydumper 使用 MYSQL_TYPE_* 字段类型） */
enum enum_field_types {
    MYSQL_TYPE_DECIMAL, MYSQL_TYPE_TINY, MYSQL_TYPE_SHORT,
    MYSQL_TYPE_LONG, MYSQL_TYPE_FLOAT, MYSQL_TYPE_DOUBLE,
    MYSQL_TYPE_NULL, MYSQL_TYPE_TIMESTAMP, MYSQL_TYPE_LONGLONG,
    MYSQL_TYPE_INT24, MYSQL_TYPE_DATE, MYSQL_TYPE_TIME,
    MYSQL_TYPE_DATETIME, MYSQL_TYPE_YEAR, MYSQL_TYPE_NEWDATE,
    MYSQL_TYPE_VARCHAR, MYSQL_TYPE_BIT, MYSQL_TYPE_TIMESTAMP2,
    MYSQL_TYPE_DATETIME2, MYSQL_TYPE_TIME2, MYSQL_TYPE_TYPED_ARRAY,
    MYSQL_TYPE_INVALID, MYSQL_TYPE_BOOL, MYSQL_TYPE_JSON,
    MYSQL_TYPE_NEWDECIMAL, MYSQL_TYPE_ENUM, MYSQL_TYPE_SET,
    MYSQL_TYPE_TINY_BLOB, MYSQL_TYPE_MEDIUM_BLOB,
    MYSQL_TYPE_LONG_BLOB, MYSQL_TYPE_BLOB, MYSQL_TYPE_VAR_STRING,
    MYSQL_TYPE_STRING, MYSQL_TYPE_GEOMETRY
};

/* enum mysql_ssl_mode（mydumper connection.c 使用 SSL_MODE_*） */
enum mysql_ssl_mode {
    SSL_MODE_DISABLED,
    SSL_MODE_PREFERRED,
    SSL_MODE_REQUIRED,
    SSL_MODE_VERIFY_CA,
    SSL_MODE_VERIFY_IDENTITY
};

#define MYSQL_ERRNO 0

/* MYSQL_FIELD flags（mydumper 使用） */
#define NOT_NULL_FLAG 1
#define PRI_KEY_FLAG 2
#define UNIQUE_KEY_FLAG 4
#define MULTIPLE_KEY_FLAG 8
#define BLOB_FLAG 16
#define UNSIGNED_FLAG 32
#define ZEROFILL_FLAG 64
#define BINARY_FLAG 128
#define ENUM_FLAG 256
#define AUTO_INCREMENT_FLAG 512
#define TIMESTAMP_FLAG 1024
#define SET_FLAG 2048
#define NO_DEFAULT_VALUE_FLAG 4096
#define ON_UPDATE_NOW_FLAG 8192
#define NUM_FLAG 32768
#define PART_KEY_FLAG 16384
#define GROUP_FLAG 32768

#ifdef __cplusplus
extern "C" {
#endif

MYSQL *mysql_init(MYSQL *mysql);
MYSQL *mysql_real_connect(MYSQL *mysql, const char *host, const char *user,
                          const char *passwd, const char *db,
                          unsigned int port, const char *unix_socket,
                          unsigned long clientflag);
void mysql_close(MYSQL *mysql);
int mysql_ping(MYSQL *mysql);
int mysql_query(MYSQL *mysql, const char *q);
int mysql_real_query(MYSQL *mysql, const char *q, unsigned long length);
MYSQL_RES *mysql_store_result(MYSQL *mysql);
MYSQL_RES *mysql_use_result(MYSQL *mysql);
void mysql_free_result(MYSQL_RES *result);
MYSQL_ROW mysql_fetch_row(MYSQL_RES *result);
MYSQL_FIELD *mysql_fetch_fields(MYSQL_RES *result);
unsigned long *mysql_fetch_lengths(MYSQL_RES *result);
unsigned int mysql_num_fields(MYSQL_RES *result);
my_ulonglong mysql_num_rows(MYSQL_RES *result);
void mysql_data_seek(MYSQL_RES *result, my_ulonglong offset);
int mysql_next_result(MYSQL *mysql);
int mysql_select_db(MYSQL *mysql, const char *db);
unsigned long mysql_real_escape_string(MYSQL *mysql, char *to,
                                       const char *from, unsigned long length);
unsigned long mysql_hex_string(char *to, const char *from, unsigned long length);
const char *mysql_error(MYSQL *mysql);
unsigned int mysql_errno(MYSQL *mysql);
const char *mysql_sqlstate(MYSQL *mysql);
unsigned int mysql_warning_count(MYSQL *mysql);
const char *mysql_character_set_name(MYSQL *mysql);
int mysql_set_character_set(MYSQL *mysql, const char *csname);
int mysql_options(MYSQL *mysql, int option, const void *arg);
int mysql_options4(MYSQL *mysql, int option, const void *arg, const void *arg2);
unsigned long mysql_get_server_version(MYSQL *mysql);
unsigned long mysql_thread_id(MYSQL *mysql);
my_ulonglong mysql_affected_rows(MYSQL *mysql);
my_ulonglong mysql_insert_id(MYSQL *mysql);
unsigned int mysql_field_count(MYSQL *mysql);
int mysql_library_init(int argc, char **argv, char **groups);
void mysql_library_end(void);
int mysql_thread_init(void);
void mysql_thread_end(void);
const char *mysql_get_client_info(void);
const char *mysql_get_host_info(MYSQL *mysql);
const char *mysql_get_server_info(MYSQL *mysql);
int mysql_ssl_set(MYSQL *mysql, const char *key, const char *cert,
                  const char *ca, const char *capath, const char *cipher);

#ifdef __cplusplus
}
#endif

#endif /* MYSQL_STUB_H */

/* glibc getpass() stub（OHOS libc 无） */
char *getpass(const char *prompt);
