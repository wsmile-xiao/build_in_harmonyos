/* Consumer check: a deny rule must produce a disruptive intervention. */
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

    RulesSet *rules = msc_create_rules_set();
    CHECK(rules != NULL, "msc_create_rules_set returns set");

    const char *error = NULL;
    int rc = msc_rules_add(rules,
        "SecRuleEngine On\n"
        "SecRule ARGS:testparam \"@contains test\" \"id:1234,deny,status:403\"",
        &error);
    CHECK(rc >= 0, "deny rule loads");
    if (error != NULL) {
        printf("rules error: %s\n", error);
        msc_rules_error_cleanup(error);
        failures++;
    }

    Transaction *txn = msc_new_transaction(msc, rules, NULL);
    CHECK(txn != NULL, "transaction created");

    CHECK(msc_process_connection(txn, "127.0.0.1", 12345, "127.0.0.1", 80) != 0,
        "process connection");
    CHECK(msc_process_uri(txn, "http://localhost/?testparam=test", "GET", "1.1") != 0,
        "process hostile uri");
    CHECK(msc_process_request_headers(txn) != 0, "process request headers");
    CHECK(msc_process_request_body(txn) != 0, "process request body");

    ModSecurityIntervention it;
    memset(&it, 0, sizeof(it));
    it.status = 200;
    (void)msc_intervention(txn, &it);
    CHECK(it.status == 403 || it.disruptive != 0, "deny rule triggers intervention");
    msc_intervention_cleanup(&it);

    msc_transaction_cleanup(txn);
    CHECK(msc_rules_cleanup(rules) != 0, "rules cleanup ok");
    msc_cleanup(msc);

    if (failures != 0) {
        printf("FAILED: %d checks\n", failures);
        return 1;
    }
    printf("WAF BLOCK CHECK PASSED\n");
    return 0;
}
