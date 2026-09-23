/* Consumer check: libmodsecurity C API lifecycle (benign transaction). */
#include <stdio.h>
#include <string.h>

#include "modsecurity/modsecurity.h"
#include "modsecurity/rules_set.h"
#include "modsecurity/transaction.h"
#include "modsecurity/intervention.h"

static int failures = 0;

#define CHECK(cond, label) do { \
    if (cond) { \
        printf("[pass] %s\n", label); \
    } else { \
        printf("[fail] %s\n", label); \
        failures++; \
    } \
} while (0)

int main(void) {
    ModSecurity *msc = msc_init();
    CHECK(msc != NULL, "msc_init returns instance");

    const char *who = msc_who_am_i(msc);
    CHECK(who != NULL && strstr(who, "ModSecurity") != NULL, "whoAmI mentions ModSecurity");

    RulesSet *rules = msc_create_rules_set();
    CHECK(rules != NULL, "msc_create_rules_set returns set");

    const char *error = NULL;
    int rc = msc_rules_add(rules,
        "SecRuleEngine On\n"
        "SecRule ARGS \"@rx test\" \"id:1,phase:2,pass,t:none\"",
        &error);
    CHECK(rc >= 0, "msc_rules_add accepts inline rules");
    if (error != NULL) {
        printf("rules error: %s\n", error);
        msc_rules_error_cleanup(error);
        failures++;
    }

    Transaction *txn = msc_new_transaction(msc, rules, NULL);
    CHECK(txn != NULL, "msc_new_transaction returns transaction");

    CHECK(msc_process_connection(txn, "127.0.0.1", 12345, "127.0.0.1", 80) != 0,
        "msc_process_connection runs");
    CHECK(msc_process_uri(txn, "http://localhost/test?a=b", "GET", "1.1") != 0,
        "msc_process_uri runs");
    CHECK(msc_process_request_headers(txn) != 0, "msc_process_request_headers runs");
    CHECK(msc_process_request_body(txn) != 0, "msc_process_request_body runs");
    CHECK(msc_process_response_headers(txn, 200, "HTTP/1.1") != 0,
        "msc_process_response_headers runs");
    CHECK(msc_process_response_body(txn) != 0, "msc_process_response_body runs");

    ModSecurityIntervention it;
    memset(&it, 0, sizeof(it));
    it.status = 200;
    (void)msc_intervention(txn, &it);
    CHECK(it.status == 200, "benign transaction has no disruptive intervention");
    msc_intervention_cleanup(&it);

    CHECK(msc_process_logging(txn) != 0, "msc_process_logging runs");

    msc_transaction_cleanup(txn);
    CHECK(msc_rules_cleanup(rules) != 0, "msc_rules_cleanup ok");
    msc_cleanup(msc);

    if (failures != 0) {
        printf("FAILED: %d checks\n", failures);
        return 1;
    }
    printf("ALL C API CHECKS PASSED\n");
    return 0;
}
