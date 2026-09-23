/*
 * Consumer test for cyrus-sasl-sql 2.1.28 (R34).
 *
 * Goal: prove the SQL auxprop plugin is really registered inside the
 * static libsasl2 — not merely that the library links.
 *
 * Discriminator
 * -------------
 * lib/auxprop.c:sasl_auxprop_store() resolves the `auxprop_plugin`
 * option through the caller's SASL_CB_GETOPT callback and walks the
 * statically registered auxprop list looking for a name match:
 *
 *     if (total_plugins == 0) {
 *         _sasl_log(NULL, SASL_LOG_ERR,
 *                   "could not find auxprop plugin, was searching for %s",
 *                   plist);          // plist = the configured name
 *         return SASL_FAIL;
 *     }
 *
 * So with `auxprop_plugin: sql` a call that reaches the plugin returns
 * SASL_OK, while an unregistered name returns SASL_FAIL. The second case
 * is asserted too, as an in-process negative control: it would fail if
 * the check were vacuous (e.g. if sasl_auxprop_store() returned SASL_OK
 * unconditionally).
 *
 * The NULL propctx keeps the call on the plugin's "am I enabled?" path
 * (plugins/sql.c: `if (!ctx && sql_exists(sql_insert) &&
 * sql_exists(sql_update)) return SASL_OK;`), so no database file, table
 * layout, or engine connection is needed. db_none/STATIC_SASLDB is not
 * configured as the requested plugin, so a match can only come from SQL.
 *
 * Out of scope: a real query against a live SQLite database (needs a
 * table schema and a sql_select statement); the package-level check is
 * plugin registration, which is what the recipe enables.
 */

#include <stdio.h>
#include <string.h>

#include <sasl/sasl.h>

/* Flipped between the positive and negative cases. */
static const char *g_auxprop_plugin = "sql";

static int getopt_cb(void *context, const char *plugin_name,
                     const char *option, const char **result,
                     unsigned *len)
{
    (void)context;
    (void)plugin_name;

    if (result == NULL) {
        return SASL_BADPARAM;
    }

    if (strcmp(option, "auxprop_plugin") == 0) {
        *result = g_auxprop_plugin;
    } else if (strcmp(option, "sql_engine") == 0) {
        *result = "sqlite3";
    } else if (strcmp(option, "sql_insert") == 0) {
        *result = "INSERT INTO users (username, password) "
                  "VALUES ('%u', '%p')";
    } else if (strcmp(option, "sql_update") == 0) {
        *result = "UPDATE users SET password = '%p' WHERE username = '%u'";
    } else if (strcmp(option, "sql_select") == 0) {
        *result = "SELECT password FROM users WHERE username = '%u'";
    } else if (strcmp(option, "sql_hostnames") == 0) {
        *result = "";
    } else if (strcmp(option, "sql_database") == 0) {
        *result = "sasldb";
    } else if (strcmp(option, "sql_user") == 0) {
        *result = "";
    } else if (strcmp(option, "sql_passwd") == 0) {
        *result = "";
    } else {
        return SASL_FAIL;   /* SASL_FAIL == "no such option" here */
    }

    if (len != NULL) {
        *len = (unsigned)strlen(*result);
    }
    return SASL_OK;
}

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    printf("  ok   %s\n", message);
    return 0;
}

int main(void)
{
    int failures = 0;

    const sasl_callback_t callbacks[] = {
        { SASL_CB_GETOPT, (int (*)(void))getopt_cb, NULL },
        { SASL_CB_LIST_END, NULL, NULL }
    };

    printf("cyrus-sasl-sql consumer checks:\n");

    /* ---- library identity ---- */
    const char *implementation = NULL;
    const char *version = NULL;
    int major = 0, minor = 0, step = 0, patch = 0;
    sasl_version_info(&implementation, &version, &major, &minor,
                      &step, &patch);
    failures += check(implementation != NULL,
                      "implementation string is available");
    failures += check(version != NULL, "version string is available");
    failures += check(major == 2 && minor == 1,
                      "major/minor version is 2.1");

    int result = sasl_server_init(callbacks, "cyrus-sasl-sql-test");
    failures += check(result == SASL_OK, "sasl_server_init succeeds");
    if (result != SASL_OK) {
        fprintf(stderr, "cannot continue without server init\n");
        return 1;
    }

    sasl_conn_t *conn = NULL;
    result = sasl_server_new("smtp", "localhost", NULL, NULL, NULL,
                             callbacks, 0, &conn);
    failures += check(result == SASL_OK && conn != NULL,
                      "sasl_server_new creates a connection");

    if (conn != NULL) {
        /*
         * Positive case: `auxprop_plugin: sql` must resolve to the
         * statically registered SQL auxprop plugin.
         */
        g_auxprop_plugin = "sql";
        result = sasl_auxprop_store(conn, NULL, "ken");
        failures += check(result == SASL_OK,
                          "auxprop_plugin 'sql' resolves to the SQL plugin "
                          "(sasl_auxprop_store -> SASL_OK)");

        /*
         * Negative control: a name that is not registered must NOT
         * resolve — otherwise the assertion above would be vacuous.
         */
        g_auxprop_plugin = "no_such_auxprop_plugin";
        int control = sasl_auxprop_store(conn, NULL, "ken");
        failures += check(control != SASL_OK,
                          "negative control: unregistered auxprop_plugin "
                          "is rejected (SASL_FAIL)");

        g_auxprop_plugin = "sql";

        /* propctx plumbing: the SQL plugin is an auxprop provider, so a
         * request must be accepted (it does not query until lookup). */
        const char *props[] = { "cmusaslsecretPLAIN", NULL };
        result = sasl_auxprop_request(conn, props);
        failures += check(result == SASL_OK,
                          "sasl_auxprop_request accepts a property request");
        failures += check(sasl_auxprop_getctx(conn) != NULL,
                          "sasl_auxprop_getctx returns a property context");

        sasl_dispose(&conn);
    }

    sasl_done();

    if (failures != 0) {
        printf("\nFAILED: %d check(s)\n", failures);
        return 1;
    }

    printf("\nOK: cyrus-sasl-sql consumer checks passed (%s %s; "
           "SQL auxprop plugin registered)\n",
           implementation ? implementation : "(null)",
           version ? version : "(null)");
    return 0;
}
