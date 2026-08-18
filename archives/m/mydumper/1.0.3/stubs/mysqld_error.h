/* Minimal stub of MySQL mysqld_error.h for OHOS (no MySQL client).
 * Server error codes used by myloader. SPDX-License-Identifier: GPL-2.0-only */
#ifndef MYSQL_MYSQLD_ERROR_STUB_H
#define MYSQL_MYSQLD_ERROR_STUB_H

/* Standard MySQL error codes (myloader compares against these) */
#define ER_LOCK_DEADLOCK 1213
#define ER_LOCK_WAIT_TIMEOUT 1205

/* mydumper/myloader specific codes (values arbitrary, classification only) */
#define ER_CHECKSUMS 10001
#define ER_GTIDS 10002
#define ER_IMPORT_ALL_TABLES 10003
#define ER_IMPORT_PER_TABLE 10004
#define ER_SIZE 10005
#define ER_SIZE_NO_STREAM 10006
#define ER_TABLE 10007
#define ER_TABLE_PRESENT 10008
#define ER_TO_INT 10009
#define ER_TYPE_MARIADB 10010

#endif /* MYSQL_MYSQLD_ERROR_STUB_H */
