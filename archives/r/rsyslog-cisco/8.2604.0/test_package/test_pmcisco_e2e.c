/* test_pmcisco_e2e.c — consumer end-to-end test for the packaged
 * pmciscoios / pmcisconames rsyslog parser modules.
 *
 * The packaged artifacts are rsyslog *loadable modules*. The real consumer is
 * rsyslogd: it dlopen()s the module, calls modInit() with the host callbacks,
 * pulls the parser entry points out of queryEtryPt(), hands the module its
 * message objects and calls the parser on every incoming syslog message. This
 * test reproduces exactly that chain against the packaged .so files, so a
 * regression in the artifact (missing entry point, wrong object interface,
 * broken parse path, lost core import) fails here instead of on the target:
 *
 *   pmciscoios.so (MODULE_TYPE_PARSER, PMOD2 interface)
 *     1. dlopen(RTLD_NOW)                  -> all imports resolve
 *     2. dlsym("modInit") + modInit()      -> objUse() of glbl/parser/datetime
 *     3. queryEtryPt() surface             -> entry table intact
 *     4. GetParserName()                   -> "rsyslog.ciscoios"
 *     5. newParserInst(NULL, ...)          -> default instance built
 *     6. isCompatibleWithFeature()         -> sanitization/PRI features
 *     7. parse2(pInst, pMsg)               -> REAL parse of a Cisco IOS message:
 *          counter "6: " -> "*" -> RFC3164 timestamp (core service call) ->
 *          "%TAG:" -> MsgSetTAG/MsgSetMSGoffs/setProtocolVersion
 *     8. parse2() on malformed input       -> RS_RET_COULD_NOT_PARSE, no write
 *     9. modExit()                         -> objRelease() path
 *
 *   pmcisconames.so (MODULE_TYPE_PARSER, PMOD interface)
 *     1..3 as above, glbl->GetParseHOSTNAMEandTAG() during modInit
 *     4. GetParserName()                   -> "rsyslog.cisconames"
 *     5. parse(pMsg)                       -> REAL fix of a mangled Cisco
 *          message: the extra ": " is removed in place, iLenRawMsg/iLenMSG
 *          are decremented and RS_RET_COULD_NOT_PARSE is returned on purpose
 *     6. parse(pMsg) on a non-Cisco message-> untouched buffer, COULD_NOT_PARSE
 *
 * rsyslog_core_stub.c provides the core services the modules import (a bare
 * executable has no rsyslogd in it); its counters turn "the module code ran"
 * into assertions. Every core service call the module is supposed to make is
 * asserted with its argument, so a no-op or stub-only test cannot pass.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rsyslog_core_stub.h"

/* ABI shapes taken from runtime/module-template.h of the same upstream version
 * (BEGINmodInit / BEGINqueryEtryPt / BEGINparse2 / BEGINparse / BEGINmodExit). */
typedef int (*etrypt_f)(void);
typedef int (*query_f)(unsigned char *name, etrypt_f *ppEtryPoint);
typedef int (*host_query_f)(unsigned char *name, void (**ppFn)(void));
typedef int (*modinit_f)(int iIFVersRequested, int *ipIFVersProvided,
                         query_f *pQueryEtryPt, host_query_f pHostQueryEtryPt,
                         void *pModInfo);
typedef int (*modExit_f)(void);
typedef int (*getParserName_f)(unsigned char **ppSz); /* module-template.h:1223 */
typedef int (*isCompatibleWithFeature_f)(int eFeat);
typedef int (*newParserInst_f)(void *lst, void *pinst);
typedef int (*checkParserInst_f)(void *pinst);
typedef int (*freeParserInst_f)(void *pInst);
typedef int (*parse2_f)(void *pInst, void *pMsg);
typedef int (*parse_f)(void *pMsg);

/* feature ids from runtime/syslogd-types.h:50-51 */
#define FEATURE_AUTOMATIC_SANITAZION 3
#define FEATURE_AUTOMATIC_PRI_PARSING 4

/* The message stand-in must have the upstream smsg_t layout: both modules read
 * iLenRawMsg/offAfterPRI/pszRawMsg, pmciscoios additionally hands tTIMESTAMP to
 * the core date parser and looks at dfltTZ, pmcisconames rewrites the raw
 * buffer in place. */
_Static_assert(sizeof(stub_msg_t) == STUB_MSG_SIZE, "smsg stand-in size mismatch");
_Static_assert(offsetof(stub_msg_t, offAfterPRI) == STUB_MSG_OFF_OFFAFTERPRI, "offAfterPRI offset");
_Static_assert(offsetof(stub_msg_t, iLenRawMsg) == STUB_MSG_OFF_ILENRAWMSG, "iLenRawMsg offset");
_Static_assert(offsetof(stub_msg_t, iLenMSG) == STUB_MSG_OFF_ILENMSG, "iLenMSG offset");
_Static_assert(offsetof(stub_msg_t, pszRawMsg) == STUB_MSG_OFF_PSZRAWMSG, "pszRawMsg offset");
_Static_assert(offsetof(stub_msg_t, tTIMESTAMP) == STUB_MSG_OFF_TTIMESTAMP, "tTIMESTAMP offset");
_Static_assert(offsetof(stub_msg_t, dfltTZ) == STUB_MSG_OFF_DFLTTZ, "dfltTZ offset");

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, ...)                                     \
    do {                                                     \
        if (cond) {                                          \
            g_pass++;                                        \
        } else {                                             \
            g_fail++;                                        \
            fprintf(stderr, "  FAIL: ");                     \
            fprintf(stderr, __VA_ARGS__);                    \
            fprintf(stderr, "\n");                           \
        }                                                    \
    } while (0)

/* Entry point surface. `required` entries are part of the interface the module
 * declares it implements (module-template.h CODEqueryEtryPt_STD_MOD_QUERIES +
 * _STD_PMOD2_QUERIES/_STD_PMOD_QUERIES + _IsCompatibleWithFeature_IF_OMOD_QUERIES);
 * the others exist in some module variants only, so they are reported, not
 * asserted. */
typedef struct {
    const char *name;
    int required;
} entry_spec_t;

static const entry_spec_t kIosEntries[] = {
    {"modExit", 1},          {"parse2", 1},           {"GetParserName", 1},
    {"newParserInst", 1},    {"checkParserInst", 1},   {"freeParserInst", 1},
    {"isCompatibleWithFeature", 1},
    {"modGetID", 0},         {"getType", 0},          {"getKeepType", 0},
};
static const entry_spec_t kNamesEntries[] = {
    {"modExit", 1},          {"parse", 1},            {"GetParserName", 1},
    {"isCompatibleWithFeature", 1},
    {"modGetID", 0},         {"getType", 0},          {"getKeepType", 0},
    {"newParserInst", 0},    {"checkParserInst", 0},   {"freeParserInst", 0},
};

static etrypt_f query_one(query_f query, const char *name)
{
    etrypt_f fn = NULL;
    int rc = query((unsigned char *)name, &fn);
    if (rc != STUB_RS_RET_OK) {
        fprintf(stderr, "  note: query('%s') rc=%d\n", name, rc);
        return NULL;
    }
    return fn;
}

static void reset_observations(void)
{
    stub_host_query_calls = 0;
    stub_obj_iface_calls = 0;
    stub_use_obj_calls = 0;
    stub_release_obj_calls = 0;
    stub_reg_cfs_calls = 0;
    stub_dbgprintf_calls = 0;
    stub_msgsettag_calls = 0;
    stub_msgsettag_lastlen = 0;
    stub_msgsettag_last[0] = '\0';
    stub_msgsethostname_calls = 0;
    stub_msgsethostname_lastlen = 0;
    stub_msgsethostname_last[0] = '\0';
    stub_msgsetmsgoffs_calls = 0;
    stub_msgsetmsgoffs_last = -1;
    stub_setprotocolversion_calls = 0;
    stub_setprotocolversion_last = -1;
    stub_applydflttz_calls = 0;
    stub_dt_parse_calls = 0;
    stub_dt_parse_last[0] = '\0';
    stub_dt_parse_forced_fail = 0;
    stub_glbl_parsehostname_calls = 0;
    stub_glbl_parsehostname_ret = 1;
    stub_dbgprintf_log[0] = '\0';
}

/* Query the declared surface, assert the required entry points, and report the
 * whole table so the artifact's interface is visible in the test log. */
static void probe_entry_points(query_f query, const entry_spec_t *specs, size_t n,
                               const char *tag)
{
    size_t i;
    char surface[512] = {0};

    for (i = 0; i < n; i++) {
        etrypt_f fn = query_one(query, specs[i].name);
        if (specs[i].required) {
            CHECK(fn != NULL, "%s: required entry point '%s' missing", tag, specs[i].name);
        }
        if (fn != NULL) {
            if (strlen(surface) + strlen(specs[i].name) + 2 < sizeof(surface)) {
                strncat(surface, specs[i].name, sizeof(surface) - strlen(surface) - 1);
                strncat(surface, " ", sizeof(surface) - strlen(surface) - 1);
            }
        }
    }
    printf("%s: entry points resolved: %s\n", tag, surface[0] ? surface : "(none)");
}

static void fill_msg(stub_msg_t *msg, char *raw, int len)
{
    memset(msg, 0, sizeof(*msg));
    msg->pszRawMsg = (unsigned char *)raw;
    msg->offAfterPRI = 0;
    msg->iLenRawMsg = len;
    msg->iLenMSG = len;
    msg->dfltTZ[0] = '\0';
}

/* ------------------------------------------------------------------ */
/* pmciscoios: MODULE_TYPE_PARSER with the PMOD2 interface (parse2)   */
/* ------------------------------------------------------------------ */
static void test_pmciscoios(void)
{
    const char *name = getenv("PMCISCO_IOS_MODULE");
    void *h;
    modinit_f modInit;
    query_f query = NULL;
    int vers = 0;
    int rc;
    getParserName_f GetParserName;
    newParserInst_f newParserInst;
    checkParserInst_f checkParserInst;
    freeParserInst_f freeParserInst;
    modExit_f modExit;
    isCompatibleWithFeature_f isCompatibleWithFeature;
    parse2_f parse2;
    struct {
        int bOriginPresent;
        int bXrPresent;
    } def_inst = {0, 0};
    void *inst_from_module = (void *)0x5eed; /* sentinel: did the module publish it? */
    stub_msg_t msg;
    char raw[512];
    char raw_before[512];

    printf("\n=== pmciscoios.so consumer end-to-end ===\n");
    reset_observations();

    /* 1. load the packaged module like rsyslogd does */
    h = dlopen(name, RTLD_NOW | RTLD_LOCAL);
    CHECK(h != NULL, "dlopen(%s) failed: %s", name, dlerror());
    if (h == NULL)
        return;
    modInit = (modinit_f)dlsym(h, "modInit");
    CHECK(modInit != NULL, "dlsym(modInit) failed: %s", dlerror());
    if (modInit == NULL) {
        dlclose(h);
        return;
    }

    /* 2. modInit: the module queried the host for the object subsystem and
     *    acquired glbl/parser/datetime through it (pmciscoios.c:273-275). */
    rc = modInit(1, &vers, &query, (host_query_f)stub_host_query, NULL);
    CHECK(rc == STUB_RS_RET_OK, "modInit rc=%d", rc);
    CHECK(vers > 0, "modInit did not report an interface version: %d", vers);
    CHECK(stub_host_query_calls >= 2, "host query callback called %d times (expected >= 2)",
          stub_host_query_calls);
    CHECK(stub_obj_iface_calls == 1, "objGetObjInterface called %d times (expected 1)",
          stub_obj_iface_calls);
    CHECK(stub_use_obj_calls == 3, "obj.UseObj called %d times (expected glbl/parser/datetime = 3)",
          stub_use_obj_calls);
    CHECK(stub_use_obj_saw("glbl"), "module did not acquire the glbl object (%s)",
          stub_use_obj_seen_names());
    CHECK(stub_use_obj_saw("parser"), "module did not acquire the parser object (%s)",
          stub_use_obj_seen_names());
    CHECK(stub_use_obj_saw("datetime"), "module did not acquire the datetime object (%s)",
          stub_use_obj_seen_names());
    CHECK(query != NULL, "modInit did not return a queryEtryPt function");
    if (query == NULL) {
        dlclose(h);
        return;
    }

    /* 3. interface surface + parser name */
    probe_entry_points(query, kIosEntries, sizeof(kIosEntries) / sizeof(kIosEntries[0]), "pmciscoios");
    GetParserName = (getParserName_f)query_one(query, "GetParserName");
    if (GetParserName != NULL) {
        unsigned char *pname = NULL;
        int nrc = GetParserName(&pname);
        CHECK(nrc == STUB_RS_RET_OK && pname != NULL &&
                  strcmp((const char *)pname, "rsyslog.ciscoios") == 0,
              "GetParserName() rc=%d name='%s' (expected 'rsyslog.ciscoios')", nrc,
              pname != NULL ? (const char *)pname : "(null)");
    }
    newParserInst = (newParserInst_f)query_one(query, "newParserInst");
    checkParserInst = (checkParserInst_f)query_one(query, "checkParserInst");
    freeParserInst = (freeParserInst_f)query_one(query, "freeParserInst");
    modExit = (modExit_f)query_one(query, "modExit");
    isCompatibleWithFeature =
        (isCompatibleWithFeature_f)query_one(query, "isCompatibleWithFeature");

    /* 4. instance creation through the module's own entry point */
    if (newParserInst != NULL) {
        rc = newParserInst(NULL, &inst_from_module);
        CHECK(rc == STUB_RS_RET_OK, "newParserInst(NULL) rc=%d", rc);
        CHECK(strstr(stub_dbgprintf_log, "newParserInst (pmciscoios)") != NULL,
              "newParserInst did not log through the core logging service");
    }
    if (checkParserInst != NULL) {
        void *inst = (inst_from_module != (void *)0x5eed) ? inst_from_module : (void *)&def_inst;
        rc = checkParserInst(inst);
        CHECK(rc == STUB_RS_RET_OK, "checkParserInst rc=%d", rc);
    }

    /* 5. feature declaration (pmciscoios.c:63-67) */
    if (isCompatibleWithFeature != NULL) {
        CHECK(isCompatibleWithFeature(FEATURE_AUTOMATIC_SANITAZION) == STUB_RS_RET_OK,
              "automatic sanitization not declared as supported");
        CHECK(isCompatibleWithFeature(FEATURE_AUTOMATIC_PRI_PARSING) == STUB_RS_RET_OK,
              "automatic PRI parsing not declared as supported");
        CHECK(isCompatibleWithFeature(0) != STUB_RS_RET_OK,
              "unknown feature declared as supported");
    }

    /* 6. the real parse path: a Cisco IOS message as IOS emits it */
    parse2 = (parse2_f)query_one(query, "parse2");
    CHECK(parse2 != NULL, "parse2 missing");
    if (parse2 != NULL) {
        const char *text =
            "6: *Jan  1 00:00:00: %LINK-3-UPDOWN: Interface GigabitEthernet0/1, "
            "changed state to up";
        int len = (int)strlen(text);
        int offs;
        const char *expected_tag = "%LINK-3-UPDOWN:";

        memset(raw, 0, sizeof(raw));
        memcpy(raw, text, (size_t)len + 1);
        memcpy(raw_before, raw, sizeof(raw));
        fill_msg(&msg, raw, len);

        rc = parse2((void *)&def_inst, (void *)&msg);
        CHECK(rc == STUB_RS_RET_OK, "parse2 rc=%d (expected RS_RET_OK)", rc);
        CHECK(stub_dt_parse_calls == 1,
              "the packaged module did not use the core datetime service (%d calls)",
              stub_dt_parse_calls);
        CHECK(strncmp(stub_dt_parse_last, "Jan  1 00:00:00: %LINK-3-UPDOWN:", 32) == 0,
              "core datetime service got '%s' instead of the timestamp cursor",
              stub_dt_parse_last);
        CHECK(stub_dt_parse_last_ret == STUB_RS_RET_OK,
              "core datetime service returned %d (lenMsg=%d) for '%s'",
              stub_dt_parse_last_ret, stub_dt_parse_last_len, stub_dt_parse_last);
        CHECK(stub_msgsettag_calls == 1, "MsgSetTAG called %d times (expected 1)",
              stub_msgsettag_calls);
        CHECK(stub_msgsettag_lastlen == (int)strlen(expected_tag),
              "MsgSetTAG len=%d (expected %d)", stub_msgsettag_lastlen,
              (int)strlen(expected_tag));
        CHECK(strcmp(stub_msgsettag_last, expected_tag) == 0, "MsgSetTAG value='%s' (expected '%s')",
              stub_msgsettag_last, expected_tag);
        CHECK(stub_msgsethostname_calls == 0,
              "MsgSetHOSTNAME called %d times although origin is not present",
              stub_msgsethostname_calls);
        CHECK(stub_msgsetmsgoffs_calls == 1, "MsgSetMSGoffs called %d times (expected 1)",
              stub_msgsetmsgoffs_calls);
        offs = stub_msgsetmsgoffs_last;
        CHECK(offs == (int)strlen("6: *Jan  1 00:00:00: %LINK-3-UPDOWN:"),
              "MsgSetMSGoffs=%d (expected %d)", offs,
              (int)strlen("6: *Jan  1 00:00:00: %LINK-3-UPDOWN:"));
        CHECK(offs > 0 && offs < len && strcmp(raw + offs, " Interface GigabitEthernet0/1, "
                                                          "changed state to up") == 0,
              "message offset %d does not point at the message body: '%s'", offs,
              (offs > 0 && offs < len) ? raw + offs : "(out of range)");
        CHECK(stub_setprotocolversion_calls == 1,
              "setProtocolVersion called %d times (expected 1)", stub_setprotocolversion_calls);
        CHECK(stub_setprotocolversion_last == 0 /* MSG_LEGACY_PROTOCOL, msg.h:165 */,
              "protocol version set to %d (expected MSG_LEGACY_PROTOCOL=0)",
              stub_setprotocolversion_last);
        CHECK(memcmp(raw, raw_before, sizeof(raw)) == 0,
              "pmciscoios must not modify the raw message");
    }

    /* 7. malformed input: no message counter at all */
    if (parse2 != NULL) {
        int tag_calls = stub_msgsettag_calls;
        int offs_calls = stub_msgsetmsgoffs_calls;
        const char *bad = "no-message-counter here";
        fill_msg(&msg, (char *)bad, (int)strlen(bad));
        rc = parse2((void *)&def_inst, (void *)&msg);
        CHECK(rc == STUB_RS_RET_COULD_NOT_PARSE,
              "parse2 on a counter-less message rc=%d (expected RS_RET_COULD_NOT_PARSE)", rc);
        CHECK(stub_msgsettag_calls == tag_calls,
              "parse2 wrote a TAG although parsing had to fail");
        CHECK(stub_msgsetmsgoffs_calls == offs_calls,
              "parse2 wrote a MSG offset although parsing had to fail");
    }

    /* 8. malformed input: valid counter, broken timestamp */
    if (parse2 != NULL) {
        int tag_calls = stub_msgsettag_calls;
        const char *bad = "6: not-a-timestamp: %X: y";
        fill_msg(&msg, (char *)bad, (int)strlen(bad));
        rc = parse2((void *)&def_inst, (void *)&msg);
        CHECK(rc == STUB_RS_RET_COULD_NOT_PARSE,
              "parse2 with a broken timestamp rc=%d (expected RS_RET_COULD_NOT_PARSE)", rc);
        CHECK(stub_msgsettag_calls == tag_calls, "parse2 wrote a TAG on a timestamp failure");
    }

    /* 9. teardown */
    if (modExit != NULL) {
        rc = modExit();
        CHECK(rc == STUB_RS_RET_OK, "modExit rc=%d", rc);
        CHECK(stub_release_obj_calls >= 3,
              "objRelease called %d times during modExit (expected >= 3)",
              stub_release_obj_calls);
    }
    if (inst_from_module != (void *)0x5eed && freeParserInst != NULL) {
        /* the module published its instance, so it may be freed through the
         * module's own entry point */
        rc = freeParserInst(inst_from_module);
        CHECK(rc == STUB_RS_RET_OK, "freeParserInst rc=%d", rc);
    } else {
        printf("note: pmciscoios keeps its parser instance module-internal in this "
               "upstream version — freeParserInst() not called\n");
    }
    CHECK(dlclose(h) == 0, "dlclose failed: %s", dlerror());
}

/* ------------------------------------------------------------------ */
/* pmcisconames: MODULE_TYPE_PARSER with the PMOD interface (parse)   */
/* ------------------------------------------------------------------ */
static void test_pmcisconames(void)
{
    const char *name = getenv("PMCISCO_NAMES_MODULE");
    void *h;
    modinit_f modInit;
    query_f query = NULL;
    int vers = 0;
    int rc;
    getParserName_f GetParserName;
    parse_f parse;
    modExit_f modExit;
    isCompatibleWithFeature_f isCompatibleWithFeature;
    stub_msg_t msg;
    char raw[512];
    char raw_before[512];
    const char *mangled =
        "Jan  1 00:00:00 hostname : %ASA-1-000000: Built inbound ICMP connection";

    printf("\n=== pmcisconames.so consumer end-to-end ===\n");
    reset_observations();

    h = dlopen(name, RTLD_NOW | RTLD_LOCAL);
    CHECK(h != NULL, "dlopen(%s) failed: %s", name, dlerror());
    if (h == NULL)
        return;
    modInit = (modinit_f)dlsym(h, "modInit");
    CHECK(modInit != NULL, "dlsym(modInit) failed: %s", dlerror());
    if (modInit == NULL) {
        dlclose(h);
        return;
    }

    /* modInit: this module caches the hostname/TAG global from the config
     * (contrib/pmcisconames/pmcisconames.c) — the shim observing that call is
     * the proof that the packaged module really ran its init on the target. */
    rc = modInit(1, &vers, &query, (host_query_f)stub_host_query, NULL);
    CHECK(rc == STUB_RS_RET_OK, "modInit rc=%d", rc);
    CHECK(vers > 0, "modInit did not report an interface version: %d", vers);
    CHECK(stub_obj_iface_calls == 1, "objGetObjInterface called %d times (expected 1)",
          stub_obj_iface_calls);
    CHECK(stub_glbl_parsehostname_calls >= 1,
          "module never called glbl->GetParseHOSTNAMEandTAG (%d calls)",
          stub_glbl_parsehostname_calls);
    CHECK(query != NULL, "modInit did not return a queryEtryPt function");
    if (query == NULL) {
        dlclose(h);
        return;
    }

    probe_entry_points(query, kNamesEntries, sizeof(kNamesEntries) / sizeof(kNamesEntries[0]),
                       "pmcisconames");
    GetParserName = (getParserName_f)query_one(query, "GetParserName");
    if (GetParserName != NULL) {
        unsigned char *pname = NULL;
        int nrc = GetParserName(&pname);
        CHECK(nrc == STUB_RS_RET_OK && pname != NULL &&
                  strcmp((const char *)pname, "rsyslog.cisconames") == 0,
              "GetParserName() rc=%d name='%s' (expected 'rsyslog.cisconames')", nrc,
              pname != NULL ? (const char *)pname : "(null)");
    }
    modExit = (modExit_f)query_one(query, "modExit");
    isCompatibleWithFeature =
        (isCompatibleWithFeature_f)query_one(query, "isCompatibleWithFeature");
    if (isCompatibleWithFeature != NULL) {
        CHECK(isCompatibleWithFeature(FEATURE_AUTOMATIC_SANITAZION) == STUB_RS_RET_OK,
              "automatic sanitization not declared as supported");
        CHECK(isCompatibleWithFeature(FEATURE_AUTOMATIC_PRI_PARSING) == STUB_RS_RET_OK,
              "automatic PRI parsing not declared as supported");
    }

    /* the real parse path: a mangled Cisco message (hostname followed by
     * " : %FACILITY-...") must be repaired in place and then handed on to the
     * next parser, i.e. COULD_NOT_PARSE is the *success* return here
     * (contrib/pmcisconames/pmcisconames.c:134-143). */
    parse = (parse_f)query_one(query, "parse");
    CHECK(parse != NULL, "parse missing");
    if (parse != NULL) {
        int len = (int)strlen(mangled);
        memset(raw, 0, sizeof(raw));
        memcpy(raw, mangled, (size_t)len + 1);
        fill_msg(&msg, raw, len);
        memcpy(raw_before, raw, sizeof(raw));

        rc = parse((void *)&msg);
        CHECK(rc == STUB_RS_RET_COULD_NOT_PARSE,
              "parse(mangled) rc=%d (expected RS_RET_COULD_NOT_PARSE so the fixed message "
              "is offered to the next parser)", rc);
        CHECK(strstr(raw, " : %") == NULL, "the extra ': ' was not removed: '%s'", raw);
        CHECK(strstr(raw, "hostname %ASA-1-000000: Built inbound ICMP connection") != NULL,
              "message body not repaired as expected: '%s'", raw);
        CHECK(msg.iLenRawMsg == len - 2, "iLenRawMsg=%d (expected %d)", msg.iLenRawMsg, len - 2);
        CHECK(msg.iLenMSG == len - 2, "iLenMSG=%d (expected %d)", msg.iLenMSG, len - 2);

        /* a message that is not a mangled Cisco log must stay untouched */
        {
            const char *plain = "Jan  1 00:00:00 host plain syslog message body";
            int plen = (int)strlen(plain);
            memset(raw, 0, sizeof(raw));
            memcpy(raw, plain, (size_t)plen + 1);
            fill_msg(&msg, raw, plen);
            memcpy(raw_before, raw, sizeof(raw));
            rc = parse((void *)&msg);
            CHECK(rc == STUB_RS_RET_COULD_NOT_PARSE, "parse(plain) rc=%d", rc);
            CHECK(memcmp(raw, raw_before, sizeof(raw)) == 0,
                  "a non-Cisco message must not be modified: '%s'", raw);
            CHECK(msg.iLenRawMsg == plen && msg.iLenMSG == plen,
                  "lengths changed on a non-Cisco message (%d/%d)", msg.iLenRawMsg, msg.iLenMSG);
        }
    }

    if (modExit != NULL) {
        rc = modExit();
        CHECK(rc == STUB_RS_RET_OK, "modExit rc=%d", rc);
    }
    CHECK(dlclose(h) == 0, "dlclose failed: %s", dlerror());
}

int main(void)
{
    const char *ios = getenv("PMCISCO_IOS_MODULE");
    const char *names = getenv("PMCISCO_NAMES_MODULE");

    /* unbuffered: if a packaged module ever brings the process down, the CI log
     * still shows how far the consumer got */
    setvbuf(stdout, NULL, _IONBF, 0);
    setvbuf(stderr, NULL, _IONBF, 0);

    if (ios == NULL || names == NULL) {
        fprintf(stderr, "PMCISCO_IOS_MODULE / PMCISCO_NAMES_MODULE must be set\n");
        return 2;
    }
    test_pmciscoios();
    test_pmcisconames();

    printf("\n-- core logging callback output --\n%s\n", stub_dbgprintf_log);
    printf("dbgprintf calls: %d\n", stub_dbgprintf_calls);
    printf("E2E_ASSERTIONS_OK=%d E2E_ASSERTIONS_FAILED=%d\n", g_pass, g_fail);
    return (g_fail == 0) ? 0 : 1;
}
