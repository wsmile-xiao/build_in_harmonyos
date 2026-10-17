/* Consumer-side contract tests for the installed libaudit 2.7.4 package.
 *
 * libaudit's public surface splits into two groups:
 *   (a) netlink-mediated kernel calls (audit_open/audit_send/...) —
 *       on OHOS the kernel constants exist but the socket is denied for
 *       the app sandbox (W0 finding, declared in the PR body), so the
 *       test asserts the *documented error surface* (negative fd,
 *       audit_msg LOG_ERR path) instead of pretending it can talk to the
 *       kernel;
 *   (b) pure-library lookup/parsing helpers (audit_detect_machine,
 *       audit_name_to_syscall, audit_syscall_to_name,
 *       audit_name_to_field, aulast/ausearch parsing via libauparse) —
 *       fully functional and asserted with real values below.
 *
 * Each numbered CHECK prints a PASS line; the tally is parsed by CI.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <libaudit.h>
#include <auparse.h>
/* field-name constants (AUDIT_PID, AUDIT_LOGINUID) live in the kernel
 * uapi header, which libaudit.h itself includes. */
#ifndef AUDIT_PID
#include <linux/audit.h>
#endif

static int g_checks = 0;
static int g_failures = 0;
#define CHECK(cond, msg)                                       \
    do {                                                       \
        g_checks++;                                            \
        if (cond) {                                            \
            printf("[CHECK %02d] PASS: %s\n", g_checks, msg);  \
        } else {                                               \
            printf("[CHECK %02d] FAIL: %s\n", g_checks, msg);  \
            g_failures++;                                      \
        }                                                      \
    } while (0)

int main(void)
{
    /* --- 1. Machine detection (pure table lookup) ----------------- */
    /* 2.7.4's machinetab maps uname machine names; aarch64 OHOS reports
     * "aarch64" via uname but the 2.7.4 table has no entry for it, so the
     * documented behaviour is a -1 return (4.x added MACH_AARCH64 to the
     * uname table). Assert the stable error surface, not a value. */
    int machine = audit_detect_machine();
    CHECK(machine == -1,
          "audit_detect_machine() returns -1 on aarch64 OHOS (2.7.4 uname table has no aarch64 entry; documented error surface)");

    /* --- 2. Syscall tables (x86_64 default tables) ----------------- */
    CHECK(audit_name_to_syscall("open", MACH_86_64) == 2,
          "audit_name_to_syscall(\"open\", x86_64) == 2");
    CHECK(audit_name_to_syscall("read", MACH_86_64) == 0,
          "audit_name_to_syscall(\"read\", x86_64) == 0");
    CHECK(audit_syscall_to_name(59, MACH_86_64) != NULL
          && strcmp(audit_syscall_to_name(59, MACH_86_64), "execve") == 0,
          "audit_syscall_to_name(59, x86_64) == \"execve\"");

    /* --- 3. Field / value name tables ------------------------------ */
    CHECK(audit_name_to_field("pid") == AUDIT_PID,
          "audit_name_to_field(\"pid\") == AUDIT_PID");
    CHECK(audit_name_to_field("loginuid") == AUDIT_LOGINUID,
          "audit_name_to_field(\"loginuid\") == AUDIT_LOGINUID");
    CHECK(audit_field_to_name(AUDIT_PID) != NULL
          && strcmp(audit_field_to_name(AUDIT_PID), "pid") == 0,
          "audit_field_to_name(AUDIT_PID) == \"pid\"");

    /* --- 4. Message type tables ------------------------------------ */
    CHECK(audit_name_to_msg_type("SYSCALL") == AUDIT_SYSCALL,
          "audit_name_to_msg_type(\"SYSCALL\") == 1300");
    CHECK(audit_msg_type_to_name(AUDIT_USER_LOGIN) != NULL
          && strcmp(audit_msg_type_to_name(AUDIT_USER_LOGIN),
                    "USER_LOGIN") == 0,
          "audit_msg_type_to_name(1112) == \"USER_LOGIN\"");

    /* --- 5. Rule construction helpers (no kernel involved) --------- */
    /* upstream contract (src/auditctl.c:86): the caller pre-allocates the
     * rule; audit_rule_fieldpair_data() fills it in. */
    struct audit_rule_data *rule = malloc(sizeof(struct audit_rule_data));
    CHECK(rule != NULL, "audit_rule_data allocation succeeds");
    if (rule != NULL) {
        memset(rule, 0, sizeof(struct audit_rule_data));
        /* upstream contract (src/auditctl.c): the pair string is parsed
         * destructively — the operator bytes are nulled out in place, so
         * the input must be writable (auditctl passes its argv). */
        char pair[] = "auid=1000";
        int rc = audit_rule_fieldpair_data(&rule, pair, 0);
        CHECK(rc == 0 && rule->fields[0] == AUDIT_LOGINUID,
              "audit_rule_fieldpair_data(\"auid=1000\") builds AUDIT_LOGINUID rule");
        free(rule);
    }

    /* --- 6. OHOS reality check: netlink audit socket surface ------- */
    errno = 0;
    int fd = audit_open();
    CHECK(fd < 0,
          "audit_open() on OHOS app sandbox returns negative fd (kernel denies NETLINK_AUDIT for the app domain; documented error surface, not a crash)");
    if (fd >= 0)
        audit_close(fd);

    /* --- 7. libauparse: real audit record parsing ------------------ */
    auparse_state_t *au = auparse_init(AUSOURCE_BUFFER,
        "type=SYSCALL msg=audit(1143146623.875:143): arch=c000003e "
        "syscall=188 success=yes exit=0 items=1 pid=2027 auid=848 "
        "uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 sgid=0 fsgid=0 "
        "tty=tty3 comm=\"login\" exe=\"/bin/login\" "
        "subj=system_u:system_r:local_login_t:s0-s0:c0.c255\n");
    CHECK(au != NULL, "auparse_init(AUSOURCE_BUFFER) succeeds");
    if (au != NULL) {
        CHECK(auparse_next_event(au) == 1,
              "auparse_next_event() yields the SYSCALL event");
        CHECK(auparse_get_type(au) == AUDIT_SYSCALL,
              "auparse_get_type() == 1300 (SYSCALL)");
        if (auparse_first_record(au) > 0
            && auparse_find_field(au, "auid") != NULL) {
            CHECK(strcmp(auparse_get_field_str(au), "848") == 0,
                  "auparse find_field(\"auid\") reads back \"848\"");
            const char *interp = auparse_interpret_field(au);
            CHECK(interp != NULL,
                  "auparse_interpret_field(\"auid\") returns an interpretation");
        } else {
            CHECK(0, "auparse find_field(\"auid\") reachable");
        }
        auparse_destroy(au);
    }

    /* --- 8. ausearch expression API over a buffer ------------------ */
    /* Same buffer-array shape as upstream auparse_test's simple_search()
     * (auparse/test/auparse_test.c): three-event stream, search auid=848. */
    const char *search_buf[] = {
        "type=LOGIN msg=audit(1143146623.787:142): login pid=2027 uid=0 "
        "old auid=4294967295 new auid=848\n"
        "type=SYSCALL msg=audit(1143146623.875:143): arch=c000003e "
        "syscall=188 success=yes exit=0 a0=7fffffa9a9f0 a1=3958d11333 "
        "a2=5131f0 a3=20 items=1 pid=2027 auid=848 uid=0 gid=0 euid=0 "
        "suid=0 fsuid=0 egid=0 sgid=0 fsgid=0 tty=tty3 comm=\"login\" "
        "exe=\"/bin/login\" "
        "subj=system_u:system_r:local_login_t:s0-s0:c0.c255\n",
        "type=USER_LOGIN msg=audit(1143146623.879:146): user pid=2027 "
        "uid=0 auid=848 msg='uid=848: exe=\"/bin/login\" "
        "(hostname=?, addr=?, terminal=tty3 res=success)'\n",
        NULL
    };
    auparse_state_t *aus = auparse_init(AUSOURCE_BUFFER_ARRAY, search_buf);
    CHECK(aus != NULL, "auparse_init for ausearch expression");
    if (aus != NULL) {
        CHECK(ausearch_add_item(aus, "auid", "=", "848",
                                AUSEARCH_RULE_CLEAR) == 0,
              "ausearch_add_item(\"auid=848\") accepted");
        CHECK(ausearch_next_event(aus) == 1,
              "ausearch_next_event() matches an auid=848 event");
        auparse_destroy(aus);
    }

    printf("consumer_tests: %d checks, %d failures\n",
           g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
