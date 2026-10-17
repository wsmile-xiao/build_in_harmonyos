/* rsyslog_core_stub.h — minimal rsyslog core ABI shim for the packaged
 * pmciscoios / pmcisconames parser module end-to-end test.
 *
 * The packaged artifacts are rsyslog *loadable modules* (pmciscoios.so,
 * pmcisconames.so): rsyslogd dlopen()s them at runtime and the modules import
 * core services from the daemon executable. A consumer without rsyslogd must
 * supply those services itself — that is what this shim does.
 *
 * Symbol inventory comes from the module's own dynamic imports
 * (`llvm-nm -D -u`):
 *   pmciscoios.so : Debug, MsgSetHOSTNAME, MsgSetMSGoffs, MsgSetTAG,
 *                   applyDfltTZ, cnfparamsPrint, cnfparamvalsDestruct,
 *                   nvlstGetParams, r_dbgprintf, setProtocolVersion
 *   pmcisconames.so: Debug, loadConf, r_dbgprintf
 * Plus the two host callbacks the modules request in modInit()
 * (module-template.h CODEmodInit_QueryRegCFSLineHdlr):
 *   "objGetObjInterface" -> stub_obj_get_obj_interface()
 *   "regCfSysLineHdlr"   -> stub_reg_cfs_line_hdlr()
 *
 * Unlike an output module, the parser modules *dereference* the object
 * interfaces they acquire via objUse(): pmciscoios calls
 * datetime->ParseTIMESTAMP3164() on every message, pmcisconames calls
 * glbl->GetParseHOSTNAMEandTAG() during modInit(). objUse() expands to
 * `.UseObj(__FILE__, "glbl", "CORE_COMPONENT", &glbl)` (runtime/obj-types.h:398),
 * so the shim fills the module's own interface structs at the exact field
 * offsets the module was compiled against. Those offsets are ABI facts of the
 * pinned upstream version + the OHOS aarch64 toolchain and are recorded below
 * with the header they come from; the test asserts them with offsetof() against
 * its own smsg_t stand-in at compile time.
 */
#ifndef RSYSLOG_CISCO_CORE_STUB_H
#define RSYSLOG_CISCO_CORE_STUB_H

#include <stddef.h>

/* --- rsyslog status codes (runtime/rsyslog.h, upstream 8.2604.0) --- */
#define STUB_RS_RET_OK 0
#define STUB_RS_RET_COULD_NOT_PARSE (-2160) /* rsyslog.h:585 */
#define STUB_RS_RET_PARAM_ERROR (-207)

/* --- smsg_t field offsets (runtime/msg.h, aarch64-linux-ohos, clang 15) ---
 * Derived with offsetof() from the very same headers the modules were built
 * against; the stand-in struct below is compiled with _Static_assert checks so
 * a drift becomes a build error instead of a silent misread. */
#define STUB_MSG_OFF_OFFAFTERPRI 76
#define STUB_MSG_OFF_ILENRAWMSG 92
#define STUB_MSG_OFF_ILENMSG 96
#define STUB_MSG_OFF_PSZRAWMSG 112
#define STUB_MSG_OFF_TTIMESTAMP 304
#define STUB_MSG_OFF_DFLTTZ 615
#define STUB_MSG_SIZE 632

/* --- object interface offsets (runtime/obj-types.h ifBEGIN at offset 0) --- */
#define STUB_OBJIF_OFF_IFVERSION 0
#define STUB_OBJIF_OFF_IFISLOADED 4
#define STUB_OBJIF_OFF_USEOBJ 8
#define STUB_OBJIF_OFF_RELEASEOBJ 16
#define STUB_OBJIF_SIZE 128
#define STUB_DTIF_OFF_IFISLOADED 4
#define STUB_DTIF_OFF_PARSETIMESTAMP3164 24
#define STUB_DTIF_SIZE 112
#define STUB_GLBLIF_OFF_IFISLOADED 4
#define STUB_GLBLIF_OFF_GETPARSEHOSTNAMEANDTAG 464
#define STUB_GLBLIF_SIZE 496
/* CURR_IF_VERSION of the three interfaces the modules use */
#define STUB_OBJ_CURR_IF_VERSION 2
#define STUB_GLBL_CURR_IF_VERSION 10
#define STUB_DT_CURR_IF_VERSION 11

/* Consumer-side smsg_t stand-in: only the fields the parser modules read or
 * write are meaningful; everything else is padding at the upstream offsets.
 * `unsigned char *pszRawMsg` + the two int lengths are read by both modules,
 * `tTIMESTAMP` is handed to datetime->ParseTIMESTAMP3164() by pmciscoios and
 * `dfltTZ` is inspected right after. */
typedef struct stub_msg_s {
    unsigned char _pad0[STUB_MSG_OFF_OFFAFTERPRI];                 /*   0.. 75 */
    int offAfterPRI;                                               /*      76 */
    unsigned char _pad1[STUB_MSG_OFF_ILENRAWMSG - (STUB_MSG_OFF_OFFAFTERPRI + 4)];
    int iLenRawMsg;                                                /*      92 */
    int iLenMSG;                                                   /*      96 */
    unsigned char _pad2[STUB_MSG_OFF_PSZRAWMSG - (STUB_MSG_OFF_ILENMSG + 4)];
    unsigned char *pszRawMsg;                                      /*     112 */
    unsigned char _pad3[STUB_MSG_OFF_TTIMESTAMP - (STUB_MSG_OFF_PSZRAWMSG + 8)];
    unsigned char tTIMESTAMP[64];                                  /* 304..367 */
    unsigned char _pad4[STUB_MSG_OFF_DFLTTZ - (STUB_MSG_OFF_TTIMESTAMP + 64)];
    char dfltTZ[8];                                                /*     615 */
    unsigned char _pad5[STUB_MSG_SIZE - (STUB_MSG_OFF_DFLTTZ + 8)];
} stub_msg_t;

/* --- observation counters / captures read by test_pmcisco_e2e.c --- */
extern int stub_host_query_calls;       /* host query callback invocations      */
extern int stub_obj_iface_calls;        /* objGetObjInterface() invocations     */
extern int stub_use_obj_calls;          /* obj.UseObj() invocations             */
extern int stub_release_obj_calls;      /* obj.ReleaseObj() invocations         */
extern int stub_reg_cfs_calls;          /* regCfSysLineHdlr() invocations       */
extern int stub_dbgprintf_calls;        /* r_dbgprintf() invocations            */
extern int stub_msgsettag_calls;        /* MsgSetTAG() invocations              */
extern int stub_msgsettag_lastlen;      /* lenBuf of the last MsgSetTAG()       */
extern char stub_msgsettag_last[128];   /* TAG text of the last MsgSetTAG()     */
extern int stub_msgsethostname_calls;   /* MsgSetHOSTNAME() invocations         */
extern int stub_msgsethostname_lastlen;
extern char stub_msgsethostname_last[128];
extern int stub_msgsetmsgoffs_calls;    /* MsgSetMSGoffs() invocations          */
extern int stub_msgsetmsgoffs_last;     /* offs of the last MsgSetMSGoffs()     */
extern int stub_setprotocolversion_calls;
extern int stub_setprotocolversion_last;
extern int stub_applydflttz_calls;      /* applyDfltTZ() invocations            */
extern int stub_dt_parse_calls;         /* datetime->ParseTIMESTAMP3164() calls */
extern char stub_dt_parse_last[64];     /* text seen at the timestamp cursor    */
extern int stub_dt_parse_last_ret;      /* value the shim handed back           */
extern int stub_dt_parse_last_len;      /* lenMsg the module passed in          */
extern int stub_dt_parse_forced_fail;   /* test injection: make the call fail   */
extern int stub_glbl_parsehostname_calls; /* glbl->GetParseHOSTNAMEandTAG()     */
extern int stub_glbl_parsehostname_ret;   /* value returned to the module        */
extern char stub_dbgprintf_log[8192];   /* everything logged via r_dbgprintf()   */

/* obj.UseObj(name) name bookkeeping ("glbl,datetime,parser,...") */
int stub_use_obj_saw(const char *name);
const char *stub_use_obj_seen_names(void);

/* host query callback handed to modInit() (4th arg); the modules request
 * "objGetObjInterface" and "regCfSysLineHdlr" through it, using the exact
 * spelling from runtime/module-template.h CODEmodInit_QueryRegCFSLineHdlr. */
#define STUB_RS_RET_NOT_FOUND (-1000)
int stub_host_query(unsigned char *name, void (**ppFn)(void));
int stub_obj_get_obj_interface(void *pIf);      /* "objGetObjInterface"     */
int stub_reg_cfs_line_hdlr(unsigned char *pCmdName, int bChainingPermitted,
                           int eType, int (*pHdlr)(void), void *pData,
                           void *pOwnerCookie);
/* hook behind obj.UseObj() / obj.ReleaseObj() */
int stub_use_obj(const char *srcFile, unsigned char *objName, unsigned char *fileName, void *pIf);
int stub_release_obj(const char *srcFile, unsigned char *objName, unsigned char *fileName, void *pIf);

/* --- exported rsyslog core services ---
 * These keep the *upstream* symbol names on purpose: the modules record them as
 * dynamic imports and RTLD_NOW resolves by name, so `stub_`-prefixed wrappers
 * would leave the modules unloadable. Prototypes mirror the upstream headers
 * (runtime/msg.h:180-202, runtime/datetime.h, runtime/rsconf.h:294,
 * runtime/debug.h:35). */
extern int Debug;   /* runtime/debug.h:35  — module reads it only for dbgoutput */
extern void *loadConf; /* runtime/rsconf.h:294 — passed to glbl->GetParseHOSTNAMEandTAG() */

void r_dbgprintf(const char *srcname, const char *fmt, ...);
void MsgSetTAG(void *pMsg, const unsigned char *pszBuf, size_t lenBuf);
void MsgSetHOSTNAME(void *pMsg, const unsigned char *pszHOSTNAME, int lenHOSTNAME);
void MsgSetMSGoffs(void *pMsg, int offs);
void setProtocolVersion(void *pMsg, int iNewVersion);
void applyDfltTZ(void *pTime, char *tz);
void *nvlstGetParams(void *lst, void *pblk, void *pvals);
void cnfparamsPrint(void *pblk, void *pvals);
void cnfparamvalsDestruct(void *pvals, void *pblk);

#endif /* RSYSLOG_CISCO_CORE_STUB_H */
