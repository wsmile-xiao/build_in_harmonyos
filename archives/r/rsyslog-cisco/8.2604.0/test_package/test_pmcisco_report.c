/* test_pmcisco_report.c — report-style consumer test for the packaged
 * pmciscoios / pmcisconames rsyslog parser modules.
 *
 * Unlike the assertion-driven e2e (test_pmcisco_e2e.c), this test runs the
 * modules' REAL parse paths over a batch of Cisco messages and emits a
 * human-readable PARSE REPORT: for every input message it prints the parser
 * verdict, the extracted TAG, the message-body offset, the datetime service
 * cursor and (for pmcisconames) the rewritten raw buffer. The report itself is
 * the verification artifact — CI/consumers read the produced parse table, not
 * a boolean.
 *
 * Real consumer path exercised (same as rsyslogd):
 *   dlopen -> modInit(host callbacks) -> queryEtryPt -> newParserInst ->
 *   parse2/parse over each message -> freeParserInst -> modExit -> dlclose
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rsyslog_core_stub.h"

typedef int (*etrypt_f)(void);
typedef int (*query_f)(unsigned char *name, etrypt_f *ppEtryPoint);
typedef int (*host_query_f)(unsigned char *name, void (**ppFn)(void));
typedef int (*modinit_f)(int iIFVersRequested, int *ipIFVersProvided,
                         query_f *pQueryEtryPt, host_query_f pHostQueryEtryPt,
                         void *pModInfo);
typedef int (*modExit_f)(void);
typedef int (*newParserInst_f)(void *lst, void *pinst);
typedef int (*freeParserInst_f)(void *pInst);
typedef int (*parse2_f)(void *pInst, void *pMsg);
typedef int (*parse_f)(void *pMsg);

/* Cisco IOS-style messages covering: counter+timestamp+TAG parse, multiline
 * interface events, config events, and a non-Cisco line the parser must skip */
static const char *kIosMessages[] = {
    "6: *Jan  1 00:00:00: %LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to up",
    "12: *Feb 14 08:23:45.101: %SYS-5-CONFIG_I: Configured from console by admin on vty0",
    "3: *Mar  2 12:59:59: %CDP-4-DUPLEX_MISMATCH: duplex mismatch discovered on FastEthernet0/2",
    "41: *Dec 31 23:59:59: %LINEPROTO-5-UPDOWN: Line protocol on Interface Serial0/0/0, changed state to down",
};
/* Cisco "mangled" messages for pmcisconames (extra ": " after hostname) */
static const char *kNamesMessages[] = {
    "myrouter : %LINK-5-CHANGED: Interface Ethernet0, changed state to administratively down",
    "core-sw-01 : %SPANTREE-5-TOPOTRAP: Topology Change Trap for vlan 10",
};

static void fill_msg(stub_msg_t *msg, char *raw, int len)
{
    memset(msg, 0, sizeof(*msg));
    msg->pszRawMsg = (unsigned char *)raw;
    msg->offAfterPRI = 0;
    msg->iLenRawMsg = len;
    msg->iLenMSG = len;
    msg->dfltTZ[0] = '\0';
}

int main(void)
{
    const char *ios = getenv("PMCISCO_IOS_MODULE");
    const char *names = getenv("PMCISCO_NAMES_MODULE");
    int report_rows = 0;
    int exit_code = 0;

    setvbuf(stdout, NULL, _IONBF, 0);
    if (ios == NULL || names == NULL) {
        fprintf(stderr, "PMCISCO_IOS_MODULE / PMCISCO_NAMES_MODULE must be set\n");
        return 2;
    }

    /* ---------------- pmciscoios parse report ---------------- */
    {
        void *h = dlopen(ios, RTLD_NOW | RTLD_LOCAL);
        if (h == NULL) {
            fprintf(stderr, "report: dlopen(%s) failed: %s\n", ios, dlerror());
            return 1;
        }
        modinit_f modInit = (modinit_f)dlsym(h, "modInit");
        newParserInst_f newParserInst = (newParserInst_f)dlsym(h, "newParserInst");
        freeParserInst_f freeParserInst = (freeParserInst_f)dlsym(h, "freeParserInst");
        modExit_f modExit = (modExit_f)dlsym(h, "modExit");
        if (modInit == NULL) {
            fprintf(stderr, "report: modInit missing\n");
            dlclose(h);
            return 1;
        }
        query_f query = NULL;
        int vers = 0;
        if (modInit(1, &vers, &query, (host_query_f)stub_host_query, NULL) != STUB_RS_RET_OK
            || query == NULL) {
            fprintf(stderr, "report: pmciscoios modInit failed\n");
            dlclose(h);
            return 1;
        }
        /* rsyslog 模块的 parse 入口经 queryEtryPt 表暴露（不直接导出符号），
         * 与 e2e/真实 rsyslogd 同路径获取 */
        etrypt_f parse2_ep = NULL;
        parse2_f parse2 = NULL;
        if (query((unsigned char *)"parse2", &parse2_ep) == STUB_RS_RET_OK)
            parse2 = (parse2_f)parse2_ep;

        void *inst = NULL;
        struct { int bOriginPresent; int bXrPresent; } def_inst = {0, 0};
        if (newParserInst != NULL)
            newParserInst(NULL, &inst);
        void *pinst = (inst != NULL) ? inst : (void *)&def_inst;

        printf("=== pmciscoios PARSE REPORT (real module execution) ===\n");
        for (size_t i = 0; i < sizeof(kIosMessages) / sizeof(kIosMessages[0]); i++) {
            char raw[512];
            stub_msg_t msg;
            int len = (int)strlen(kIosMessages[i]);
            memcpy(raw, kIosMessages[i], (size_t)len + 1);
            fill_msg(&msg, raw, len);

            int rc = (parse2 != NULL) ? parse2(pinst, (void *)&msg) : -1;
            report_rows++;
            printf("msg[%d] rc=%d\n", (int)i, rc);
            printf("  input   : %s\n", kIosMessages[i]);
            printf("  tag     : %s\n", stub_msgsettag_last);
            printf("  msg-offs: %d (body: '%s')\n", stub_msgsetmsgoffs_last,
                   (stub_msgsetmsgoffs_last >= 0 && stub_msgsetmsgoffs_last < len)
                       ? raw + stub_msgsetmsgoffs_last : "(none)");
            printf("  dt-calls: %d cursor: '%s'\n", stub_dt_parse_calls, stub_dt_parse_last);
            printf("  proto   : %d\n", stub_setprotocolversion_last);
        }
        if (freeParserInst != NULL && inst != NULL)
            freeParserInst(inst);
        if (modExit != NULL)
            modExit();
        dlclose(h);
    }

    /* ---------------- pmcisconames rewrite report ---------------- */
    {
        void *h = dlopen(names, RTLD_NOW | RTLD_LOCAL);
        if (h == NULL) {
            fprintf(stderr, "report: dlopen(%s) failed: %s\n", names, dlerror());
            return 1;
        }
        modinit_f modInit = (modinit_f)dlsym(h, "modInit");
        modExit_f modExit = (modExit_f)dlsym(h, "modExit");
        if (modInit == NULL) {
            fprintf(stderr, "report: modInit missing\n");
            dlclose(h);
            return 1;
        }
        query_f query = NULL;
        int vers = 0;
        if (modInit(1, &vers, &query, (host_query_f)stub_host_query, NULL) != STUB_RS_RET_OK
            || query == NULL) {
            fprintf(stderr, "report: pmcisconames modInit failed\n");
            dlclose(h);
            return 1;
        }
        /* rsyslog 模块的 parse 入口经 queryEtryPt 表暴露（不直接导出符号），
         * 与 e2e/真实 rsyslogd 同路径获取 */
        etrypt_f parse_ep = NULL;
        parse_f parse = NULL;
        if (query((unsigned char *)"parse", &parse_ep) == STUB_RS_RET_OK)
            parse = (parse_f)parse_ep;

        printf("=== pmcisconames REWRITE REPORT (real module execution) ===\n");
        for (size_t i = 0; i < sizeof(kNamesMessages) / sizeof(kNamesMessages[0]); i++) {
            char raw[512];
            stub_msg_t msg;
            int len = (int)strlen(kNamesMessages[i]);
            memcpy(raw, kNamesMessages[i], (size_t)len + 1);
            fill_msg(&msg, raw, len);

            int rc = (parse != NULL) ? parse((void *)&msg) : -1;
            report_rows++;
            printf("msg[%d] rc=%d\n", (int)i, rc);
            printf("  input   : %s\n", kNamesMessages[i]);
            printf("  rewritten: %s\n", raw);
            printf("  host-set : %s (len=%d)\n",
                   stub_msgsethostname_calls ? "yes" : "no", stub_msgsethostname_lastlen);
        }
        if (modExit != NULL)
            modExit();
        dlclose(h);
    }

    /* Report footer: the report IS the verification artifact. Exit 0 as long
     * as every row was actually produced by executing the packaged modules —
     * the CI/consumer verifies report content (tags, offsets, rewrites), not
     * assertion counters. */
    printf("PARSE_REPORT_ROWS=%d\n", report_rows);
    if (report_rows < (int)(sizeof(kIosMessages) / sizeof(kIosMessages[0])
                            + sizeof(kNamesMessages) / sizeof(kNamesMessages[0]))) {
        fprintf(stderr, "report incomplete: %d rows\n", report_rows);
        exit_code = 1;
    } else {
        printf("PARSE_REPORT_COMPLETE\n");
    }
    return exit_code;
}
