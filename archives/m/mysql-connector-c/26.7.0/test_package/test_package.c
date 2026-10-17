/*
 * First-pass test: actually call an X DevAPI for C function that
 * does not require a MySQL Server connection.  mysqlx_session_options_new()
 * creates a local options object only; it does not contact the server.
 *
 * Goals verified by this test:
 *   1. <mysqlx/xapi.h> compiles with the OHOS clang toolchain (plain C)
 *   2. libmysqlcppconnx-static.a is actually linked (the symbols
 *      mysqlx_session_options_new / mysqlx_free must resolve)
 *   3. STATIC_CONCPP define is correctly propagated
 *   4. C++ runtime (used inside the static lib) is correctly pulled in
 *   5. OpenSSL transitive deps are correctly resolved
 */

#include <mysqlx/xapi.h>

int main(void)
{
    mysqlx_session_options_t *opts = mysqlx_session_options_new();
    if (opts == NULL)
        return 1;
    mysqlx_free(opts);
    return 0;
}
