#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include <odbcinst.h>
#include <sql.h>
#include <sqlext.h>

static int fail(const char *message)
{
    fprintf(stderr, "FAIL: %s\n", message);
    return 1;
}

static int expect_sql_success(SQLRETURN rc, const char *message)
{
    if (!SQL_SUCCEEDED(rc)) {
        fprintf(stderr, "FAIL: %s returned %d\n", message, (int)rc);
        return 1;
    }
    return 0;
}

int main(void)
{
    SQLHENV env = SQL_NULL_HENV;
    SQLHDBC dbc = SQL_NULL_HDBC;
    SQLCHAR state[6] = {0};
    SQLINTEGER native_error = 0;
    SQLCHAR message[SQL_MAX_MESSAGE_LENGTH] = {0};
    SQLSMALLINT message_len = 0;
    UWORD config_mode = 0;
    DWORD installer_error = 0;
    WORD installer_message_len = 0;
    char installer_message[SQL_MAX_MESSAGE_LENGTH] = {0};

    if (expect_sql_success(
            SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &env),
            "SQLAllocHandle(SQL_HANDLE_ENV)")) {
        return 1;
    }

    if (expect_sql_success(
            SQLSetEnvAttr(
                env,
                SQL_ATTR_ODBC_VERSION,
                (SQLPOINTER)(uintptr_t)SQL_OV_ODBC3,
                0),
            "SQLSetEnvAttr(SQL_ATTR_ODBC_VERSION)")) {
        SQLFreeHandle(SQL_HANDLE_ENV, env);
        return 1;
    }

    if (expect_sql_success(
            SQLAllocHandle(SQL_HANDLE_DBC, env, &dbc),
            "SQLAllocHandle(SQL_HANDLE_DBC)")) {
        SQLFreeHandle(SQL_HANDLE_ENV, env);
        return 1;
    }

    if (SQLGetDiagRec(
            SQL_HANDLE_DBC,
            dbc,
            1,
            state,
            &native_error,
            message,
            sizeof(message),
            &message_len) != SQL_NO_DATA) {
        SQLFreeHandle(SQL_HANDLE_DBC, dbc);
        SQLFreeHandle(SQL_HANDLE_ENV, env);
        return fail("fresh DBC handle should have no diagnostics");
    }

    if (expect_sql_success(SQLFreeHandle(SQL_HANDLE_DBC, dbc), "SQLFreeHandle(DBC)")) {
        SQLFreeHandle(SQL_HANDLE_ENV, env);
        return 1;
    }
    if (expect_sql_success(SQLFreeHandle(SQL_HANDLE_ENV, env), "SQLFreeHandle(ENV)")) {
        return 1;
    }

    if (!SQLGetConfigMode(&config_mode)) {
        return fail("SQLGetConfigMode failed");
    }
    if (config_mode != ODBC_USER_DSN &&
        config_mode != ODBC_SYSTEM_DSN &&
        config_mode != ODBC_BOTH_DSN) {
        return fail("SQLGetConfigMode returned an unexpected mode");
    }
    if (!SQLSetConfigMode(ODBC_BOTH_DSN)) {
        return fail("SQLSetConfigMode(ODBC_BOTH_DSN) failed");
    }
    if (!SQLValidDSN("ConanSmokeDSN")) {
        return fail("SQLValidDSN rejected a valid DSN name");
    }

    SQLInstallerError(
        1,
        &installer_error,
        installer_message,
        sizeof(installer_message),
        &installer_message_len);

    printf("PASS: unixODBC API smoke test completed\n");
    return 0;
}
