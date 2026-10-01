/* rsyslog_core_stub.h — minimal rsyslog core ABI shim for the packaged
 * omtesting module end-to-end test.
 *
 * The packaged artifact is a rsyslog *loadable module* (omtesting.so): it is
 * dlopen()ed by rsyslogd at runtime and imports core services from the daemon
 * binary (see `llvm-nm -u omtesting.so`: OMSRconstruct, OMSRdestruct,
 * cflineParseTemplateName, randomNumber, r_dbgprintf). A consumer that has no
 * rsyslogd available must therefore supply those services itself.
 *
 * This shim implements exactly the five imported core functions plus the two
 * host callbacks the module requests during modInit()
 * (module-template.h CODESTARTmodInit / CODEmodInit_QueryRegCFSLineHdlr):
 *   - host query "objGetObjInterface"  -> stub_obj_get_obj_interface()
 *   - host query "regCFSLineHdlr"      -> stub_reg_cfs_line_hdlr()
 *
 * Every callback records what the module asked for, so the E2E test can prove
 * the module really executed its real code paths (not a stub-only build).
 */
#ifndef RSYSLOG_CORE_STUB_H
#define RSYSLOG_CORE_STUB_H

/* --- rsyslog status codes actually observed by the test --- */
#define RS_RET_OK 0                /* runtime/rsret.h */
#define RS_RET_SUSPENDED (-214)    /* returned by the "fail"/"always_suspend" modes */
#define RS_RET_INCOMPATIBLE (-216) /* isCompatibleWithFeature() default */

/* --- observation counters / captures (read by test_omtesting_e2e.c) --- */
extern int stub_host_query_calls;          /* host query callback invocations */
extern int stub_obj_iface_calls;           /* objGetObjInterface() invocations */
extern int stub_reg_cfs_calls;             /* regCFSLineHdlr() invocations */
extern int stub_dbgprintf_calls;           /* r_dbgprintf() invocations */
extern int stub_omsr_construct_calls;
extern int stub_omsr_destruct_calls;
extern int stub_omsr_last_num_entries;     /* iNumEntries of the last OMSRconstruct() */
extern int stub_cfline_calls;
extern int stub_random_calls;

extern char stub_reg_cfs_lastname[64];     /* registered CFS command name */
extern int stub_reg_cfs_lasttype;          /* ecslCmdHdrlType of last registration */
extern int stub_reg_cfs_handler_present;   /* non-zero if a handler ptr was passed */
extern int stub_reg_cfs_last_chain;        /* bChainingPermitted of last registration */
extern void *stub_reg_cfs_last_data;       /* pData of last registration */
extern void *stub_reg_cfs_last_owner;      /* pOwnerCookie (== STD_LOADABLE_MODULE_ID) */

/* concatenation of everything the module logged through r_dbgprintf() */
extern char stub_dbgprintf_log[8192];

/* did the host query callback get asked for this entry point name? */
int stub_host_query_saw(const char *name);
/* list of names requested through the host query callback, comma separated */
const char *stub_host_query_seen_names(void);

/* host query callback handed to modInit() (2nd arg of modInit); the module
 * requests "objGetObjInterface" and "regCfSysLineHdlr" through it (exact names
 * as spelled by runtime/module-template.h CODEmodInit_QueryRegCFSLineHdlr). */
#define RS_RET_STUB_NOT_FOUND (-1000)
int stub_host_query(unsigned char *name, void (**ppFn)(void));

/* --- exported rsyslog core services (referenced by the module) ---
 * These are the *upstream* symbol names on purpose: omtesting.so records them as
 * dynamic imports (`llvm-nm -u omtesting.so`), and RTLD_NOW resolution matches
 * symbols by name, so `stub_`-prefixed wrappers would leave the module
 * unloadable. Prototypes mirror the upstream headers they are imported from
 * (runtime/debug.h, runtime/objomsr.h, runtime/conf.h, runtime/srUtils.h); the
 * return type is rsRetVal (int) throughout. */
void r_dbgprintf(const char *srcname, const char *fmt, ...);
int OMSRconstruct(void **ppThis, int iNumEntries);
int OMSRdestruct(void *pThis);
int cflineParseTemplateName(void *pline, void **ppOMSR, int bDoLock,
                            int iNumTpls, void *pDflt);
int randomNumber(void);
int stub_obj_get_obj_interface(void *pIf);   /* "objGetObjInterface" */
int stub_reg_cfs_line_hdlr(unsigned char *pCmdName, int bChainingPermitted,
                           int eType, int (*pHdlr)(void), void *pData,
                           void *pOwnerCookie);

#endif /* RSYSLOG_CORE_STUB_H */
