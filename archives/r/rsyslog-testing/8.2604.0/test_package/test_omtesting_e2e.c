/* test_omtesting_e2e.c — consumer end-to-end test for the packaged
 * omtesting rsyslog module.
 *
 * What is verified here is the *packaged artifact* consumed the way the real
 * consumer (rsyslogd) consumes it:
 *
 *   1. dlopen(RTLD_NOW)                     -> every import of the module resolves
 *   2. dlsym("modInit") + modInit()          -> real module init, incl. the host
 *                                              callbacks the module requests
 *   3. queryEtryPt() surface                 -> module entry point table intact
 *   4. createInstance()                      -> instance state defaults applied
 *   5. createWrkrInstance() + doAction()     -> real message delivery path runs
 *   6. tryResume()                           -> retry path runs
 *   7. freeWrkrInstance/freeInstance/modExit -> teardown path runs
 *
 * The module imports five rsyslog core services; this consumer provides them
 * through rsyslog_core_stub.c (see that file for why a shim is required).
 * Observation counters in the shim turn "the code ran" into assertions.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rsyslog_core_stub.h"

/* ABI shapes taken from runtime/module-template.h of the same upstream version
 * (BEGINmodInit / BEGINcreateInstance / BEGINcreateWrkrInstance / BEGINdoAction
 *  / BEGINtryResume / BEGINdbgPrintInstInfo / BEGINisCompatibleWithFeature /
 *  BEGINmodExit and BEGINqueryEtryPt). */
typedef int (*etrypt_f)(void);
typedef int (*query_f)(unsigned char *name, etrypt_f *ppEtryPoint);
typedef int (*host_query_f)(unsigned char *name, void (**ppFn)(void));
typedef int (*modinit_f)(int iIFVersRequested, int *ipIFVersProvided,
                         query_f *pQueryEtryPt, host_query_f pHostQueryEtryPt,
                         void *pModInfo);
typedef int (*createInstance_f)(void **ppData);
typedef int (*freeInstance_f)(void *pData);
typedef int (*createWrkrInstance_f)(void **ppWrkrData, void *pData);
typedef int (*freeWrkrInstance_f)(void *pWrkrData);
typedef int (*doAction_f)(void *pMsgData, void *pWrkrData);
typedef int (*tryResume_f)(void *pWrkrData);
typedef int (*dbgPrintInstInfo_f)(void *pModData);
typedef int (*isCompatibleWithFeature_f)(int eFeat);
typedef int (*modExit_f)(void);
/* parseSelectorAct(uchar **pp, void **ppModData, omodStringRequest_t **ppOMSR)
 *   runtime/module-template.h BEGINparseSelectorAct */
typedef int (*parseSelectorAct_f)(unsigned char **pp, void **ppModData, void **ppOMSR);

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

/* Entry points every output module must expose through queryEtryPt():
 * CODEqueryEtryPt_STD_MOD_QUERIES + CODEqueryEtryPt_STD_OMOD_QUERIES
 * + CODEqueryEtryPt_STD_OMOD8_QUERIES. Note that "createInstance" is NOT part of
 * that table: it is a static function inside the module, called by
 * parseSelectorAct() (module-template.h CODE_STD_STRING_REQUESTparseSelectorAct). */
static const char *kExpectedEntryPoints[] = {
    "modExit",           "modGetID",           "getType",
    "getKeepType",       "doAction",           "dbgPrintInstInfo",
    "freeInstance",      "parseSelectorAct",   "isCompatibleWithFeature",
    "tryResume",         "createWrkrInstance", "freeWrkrInstance",
};
#define N_EXPECTED_ENTRY_POINTS \
    (sizeof(kExpectedEntryPoints) / sizeof(kExpectedEntryPoints[0]))

static etrypt_f query_one(query_f query, const char *name)
{
    etrypt_f fn = NULL;
    int rc = query((unsigned char *)name, &fn);
    if (rc != RS_RET_OK) {
        fprintf(stderr, "  note: query('%s') rc=%d\n", name, rc);
        return NULL;
    }
    return fn;
}

int main(int argc, char **argv)
{
    const char *module = (argc > 1) ? argv[1] : getenv("OMTESTING_MODULE");
    void *h = NULL;
    modinit_f modInit = NULL;
    query_f query = NULL;
    etrypt_f fn = NULL;
    int rc = 0;
    int vers = 0;
    int uniq = 0;
    void *inst = NULL;
    void *wrkr = NULL;
    void *omsr = NULL; /* omodStringRequest_t (runtime/objomsr.h), opaque here */
    unsigned char msg[] = "omtesting-e2e-consumer-message";
    unsigned char *ppString = msg;
    doAction_f doAction = NULL;

    printf("== omtesting consumer end-to-end test ==\n");
    printf("module: %s\n", module != NULL ? module : "(null)");

    CHECK(module != NULL, "module path not provided on argv[1]/OMTESTING_MODULE");
    if (module == NULL)
        goto summary;

    /* 1. load the packaged module: RTLD_NOW resolves every import at load time,
     *    so a successful dlopen proves the shared object is self-consistent
     *    against the rsyslog core ABI it was built for. */
    h = dlopen(module, RTLD_NOW | RTLD_LOCAL);
    CHECK(h != NULL, "dlopen(RTLD_NOW) failed: %s", dlerror());
    if (h == NULL)
        goto summary;
    printf("[ok] module loaded\n");

    /* 2. modInit(): the module must request its host services and register its
     *    config directive. */
    modInit = (modinit_f)dlsym(h, "modInit");
    CHECK(modInit != NULL, "dlsym(modInit) failed: %s", dlerror());
    if (modInit == NULL)
        goto summary;

    rc = modInit(0, &vers, &query, (host_query_f)stub_host_query, NULL);
    printf("modInit -> rc=%d ifVers=%d host_query_calls=%d\n", rc, vers,
           stub_host_query_calls);
    printf("host query names: %s\n", stub_host_query_seen_names());

    CHECK(rc == RS_RET_OK, "modInit returned rc=%d", rc);
    CHECK(vers > 0, "modInit reported no interface version (vers=%d)", vers);
    CHECK(query != NULL, "modInit did not provide queryEtryPt()");
    CHECK(stub_host_query_calls >= 1,
          "module requested no host services (host_query_calls=%d)",
          stub_host_query_calls);
    CHECK(stub_host_query_saw("objGetObjInterface"),
          "module did not request objGetObjInterface");
    CHECK(stub_host_query_saw("regCfSysLineHdlr"),
          "module did not request regCfSysLineHdlr");
    CHECK(stub_obj_iface_calls == 1,
          "objGetObjInterface called %d time(s), expected 1", stub_obj_iface_calls);
    CHECK(stub_reg_cfs_calls == 1, "regCfSysLineHdlr called %d time(s), expected 1",
          stub_reg_cfs_calls);
    /* omtesting.c:349 registers a *binary config variable*:
     *   omsdRegCFSLineHdlr("actionomtestingechostdout", 0, eCmdHdlrBinary,
     *                      NULL, &cs.bEchoStdout, STD_LOADABLE_MODULE_ID)
     * The handler is therefore legitimately NULL, the target variable arrives via
     * pData, and the owner cookie must be the module's own modExit pointer
     * (module-template.h:100 STD_LOADABLE_MODULE_ID ((void *)modExit)). */
    CHECK(strcmp(stub_reg_cfs_lastname, "actionomtestingechostdout") == 0,
          "config directive registered as '%s', expected 'actionomtestingechostdout'",
          stub_reg_cfs_lastname);
    CHECK(stub_reg_cfs_last_chain == 0,
          "bChainingPermitted=%d, expected 0", stub_reg_cfs_last_chain);
    CHECK(stub_reg_cfs_last_data != NULL,
          "binary config variable registered without a data pointer");
    if (query != NULL) {
        void *mod_exit = query_one(query, "modExit");
        CHECK(mod_exit != NULL, "modExit entry point missing");
        CHECK(stub_reg_cfs_last_owner == mod_exit,
              "owner cookie %p is not the module's modExit pointer %p",
              stub_reg_cfs_last_owner, mod_exit);
    }
    printf("[ok] config directive registered: '%s' (type=%d, owner=%p)\n",
           stub_reg_cfs_lastname, stub_reg_cfs_lasttype, stub_reg_cfs_last_owner);

    if (query == NULL)
        goto summary;

    /* 3. entry point table surface */
    {
        size_t i;
        for (i = 0; i < N_EXPECTED_ENTRY_POINTS; i++) {
            fn = query_one(query, kExpectedEntryPoints[i]);
            CHECK(fn != NULL, "queryEtryPt('%s') did not provide an entry point",
                  kExpectedEntryPoints[i]);
        }
    }
    /* negative: an unknown name must not resolve */
    fn = NULL;
    rc = query((unsigned char *)"atomcode_no_such_entry_point", &fn);
    CHECK(fn == NULL, "unknown entry point name resolved to %p", (void *)fn);
    CHECK(rc != RS_RET_OK, "unknown entry point name returned rc=%d", rc);

    /* 4. parseSelectorAct(): how a consumer really obtains a module instance.
     *    createInstance() is static inside the module and thus not part of the
     *    queryEtryPt() table; parseSelectorAct() invokes it itself
     *    (module-template.h CODE_STD_STRING_REQUESTparseSelectorAct ->
     *    OMSRconstruct(), then the module's own createInstance()). The selector
     *    text is the upstream one from plugins/omtesting/omtesting.c. */
    {
        parseSelectorAct_f parseSelectorAct =
            (parseSelectorAct_f)query_one(query, "parseSelectorAct");
        static unsigned char selector[] = ":omtesting:sleep 1 0";
        unsigned char *psel = selector;

        CHECK(parseSelectorAct != NULL, "parseSelectorAct missing");
        if (parseSelectorAct == NULL)
            goto summary;
        rc = parseSelectorAct(&psel, &inst, &omsr);
        CHECK(rc == RS_RET_OK, "parseSelectorAct rc=%d", rc);
        CHECK(inst != NULL, "parseSelectorAct produced no module instance");
        CHECK(omsr != NULL, "parseSelectorAct requested no string template");
        CHECK(stub_omsr_construct_calls == 1,
              "module did not call OMSRconstruct() (calls=%d)",
              stub_omsr_construct_calls);
        CHECK(stub_omsr_last_num_entries == 1,
              "module requested %d string entries, expected 1",
              stub_omsr_last_num_entries);
        CHECK(stub_cfline_calls == 1,
              "module did not call cflineParseTemplateName() (calls=%d)",
              stub_cfline_calls);
        CHECK(psel != selector, "module did not consume the selector text");
        if (inst == NULL)
            goto summary;
        printf("[ok] parseSelectorAct -> instance %p, omsr %p, selector consumed %ld bytes\n",
               inst, omsr, (long)(psel - selector));
    }

    /* 5. dbgPrintInstInfo(): the module reports its own instance state through
     *    the core logging callback, which is captured by the shim. */
    {
        dbgPrintInstInfo_f dbgPrintInstInfo =
            (dbgPrintInstInfo_f)query_one(query, "dbgPrintInstInfo");
        CHECK(dbgPrintInstInfo != NULL, "dbgPrintInstInfo missing");
        if (dbgPrintInstInfo != NULL) {
            rc = dbgPrintInstInfo(inst);
            CHECK(rc == RS_RET_OK, "dbgPrintInstInfo rc=%d", rc);
            CHECK(strstr(stub_dbgprintf_log,
                         "Action delays rule by 1 second(s)") != NULL,
                  "instance defaults not applied, log: %s", stub_dbgprintf_log);
        }
    }

    /* 6. worker instance + real action delivery */
    {
        createWrkrInstance_f createWrkrInstance =
            (createWrkrInstance_f)query_one(query, "createWrkrInstance");
        CHECK(createWrkrInstance != NULL, "createWrkrInstance missing");
        if (createWrkrInstance == NULL)
            goto summary;
        rc = createWrkrInstance(&wrkr, inst);
        CHECK(rc == RS_RET_OK, "createWrkrInstance rc=%d", rc);
        CHECK(wrkr != NULL, "createWrkrInstance returned no worker data");
        if (wrkr == NULL)
            goto summary;
        printf("[ok] createWrkrInstance -> %p\n", wrkr);
    }

    /* 6b. isCompatibleWithFeature(): the module intentionally reports itself as
     *     incompatible with repeated message reduction. */
    {
        isCompatibleWithFeature_f isCompatibleWithFeature =
            (isCompatibleWithFeature_f)query_one(query, "isCompatibleWithFeature");
        CHECK(isCompatibleWithFeature != NULL, "isCompatibleWithFeature missing");
        if (isCompatibleWithFeature != NULL) {
            rc = isCompatibleWithFeature(0);
            CHECK(rc != RS_RET_OK,
                  "isCompatibleWithFeature unexpectedly compatible (rc=%d)", rc);
        }
    }

    /* 6c. tryResume(): mode MD_SLEEP (default) must report a successful resume. */
    {
        tryResume_f tryResume = (tryResume_f)query_one(query, "tryResume");
        CHECK(tryResume != NULL, "tryResume missing");
        if (tryResume != NULL) {
            rc = tryResume(wrkr);
            CHECK(rc == RS_RET_OK, "tryResume rc=%d", rc);
            CHECK(strstr(stub_dbgprintf_log, "tryResume() called") != NULL,
                  "tryResume did not run: %s", stub_dbgprintf_log);
        }
    }

    /* 6d. doAction(): deliver a message through the module. Default mode is
     *     MD_SLEEP with iWaitSeconds = 1, so this call takes ~1 second and
     *     returns RS_RET_OK. */
    doAction = (doAction_f)query_one(query, "doAction");
    CHECK(doAction != NULL, "doAction missing");
    if (doAction != NULL) {
        rc = doAction((void *)&ppString, wrkr);
        CHECK(rc == RS_RET_OK, "doAction rc=%d", rc);
        CHECK(strstr(stub_dbgprintf_log,
                     "received msg 'omtesting-e2e-consumer-message'") != NULL,
              "message was not delivered to the module");
    }

    /* 6e. interface version must be stable across calls (module-template.h
     *     warns modInit may be invoked again after modExit). */
    uniq = 0;
    rc = modInit(0, &uniq, &query, (host_query_f)stub_host_query, NULL);
    CHECK(rc == RS_RET_OK, "second modInit rc=%d", rc);
    CHECK(uniq == vers, "interface version changed between modInit calls (%d -> %d)",
          vers, uniq);

    /* 7. teardown */
    {
        freeWrkrInstance_f freeWrkrInstance =
            (freeWrkrInstance_f)query_one(query, "freeWrkrInstance");
        freeInstance_f freeInstance =
            (freeInstance_f)query_one(query, "freeInstance");
        modExit_f modExit = (modExit_f)query_one(query, "modExit");

        CHECK(freeWrkrInstance != NULL, "freeWrkrInstance missing");
        if (freeWrkrInstance != NULL) {
            rc = freeWrkrInstance(wrkr);
            CHECK(rc == RS_RET_OK, "freeWrkrInstance rc=%d", rc);
        }
        CHECK(freeInstance != NULL, "freeInstance missing");
        if (freeInstance != NULL) {
            rc = freeInstance(inst);
            CHECK(rc == RS_RET_OK, "freeInstance rc=%d", rc);
        }
        CHECK(modExit != NULL, "modExit missing");
        if (modExit != NULL) {
            rc = modExit();
            CHECK(rc == RS_RET_OK, "modExit rc=%d", rc);
        }
    }

    /* the core normally owns the omodStringRequest the module asked for; here
     * the consumer does, so release it through the shim. */
    if (omsr != NULL) {
        rc = OMSRdestruct(omsr);
        CHECK(rc == RS_RET_OK, "OMSRdestruct rc=%d", rc);
        omsr = NULL;
    }

    rc = dlclose(h);
    CHECK(rc == 0, "dlclose rc=%d", rc);

summary:
    printf("-- module debug output (core logging callback) --\n%s\n",
           stub_dbgprintf_log);
    printf("dbgprintf calls: %d\n", stub_dbgprintf_calls);
    printf("E2E_ASSERTIONS_OK=%d E2E_ASSERTIONS_FAILED=%d\n", g_pass, g_fail);
    return (g_fail == 0) ? 0 : 1;
}
