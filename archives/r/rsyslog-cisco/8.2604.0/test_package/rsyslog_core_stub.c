/* rsyslog_core_stub.c — see rsyslog_core_stub.h for the rationale.
 *
 * Every symbol here is intentionally *exported* (the test binary links with
 * -Wl,--export-dynamic) so that dlopen(RTLD_NOW) of pmciscoios.so /
 * pmcisconames.so resolves the modules' imports against this shim instead of a
 * running rsyslogd. Each service records what the module asked for, which turns
 * "the module code ran" into assertions in test_pmcisco_e2e.c.
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rsyslog_core_stub.h"

/* --- globals the modules read --- */
int Debug = 1;          /* runtime/debug.h:35 — non-zero so the modules' own progress
                         * logging (gated on this flag, see pmciscoios.c:2518) is observable */
void *loadConf = NULL;  /* runtime/rsconf.h:294 (handed to glbl->GetParseHOSTNAMEandTAG) */

int stub_host_query_calls = 0;
int stub_obj_iface_calls = 0;
int stub_use_obj_calls = 0;
int stub_release_obj_calls = 0;
int stub_reg_cfs_calls = 0;
int stub_dbgprintf_calls = 0;
int stub_msgsettag_calls = 0;
int stub_msgsettag_lastlen = 0;
char stub_msgsettag_last[128] = {0};
int stub_msgsethostname_calls = 0;
int stub_msgsethostname_lastlen = 0;
char stub_msgsethostname_last[128] = {0};
int stub_msgsetmsgoffs_calls = 0;
int stub_msgsetmsgoffs_last = -1;
int stub_setprotocolversion_calls = 0;
int stub_setprotocolversion_last = -1;
int stub_applydflttz_calls = 0;
int stub_dt_parse_calls = 0;
int stub_dt_parse_last_ret = -99999;
int stub_dt_parse_last_len = -1;
char stub_dt_parse_last[64] = {0};
int stub_dt_parse_forced_fail = 0;
int stub_glbl_parsehostname_calls = 0;
int stub_glbl_parsehostname_ret = 1;
char stub_dbgprintf_log[8192] = {0};

static char use_obj_names[1024] = {0};

static void stub_seen_add(const char *name)
{
    if (name == NULL)
        return;
    if (strlen(use_obj_names) + strlen(name) + 2 < sizeof(use_obj_names)) {
        if (use_obj_names[0] != '\0')
            strncat(use_obj_names, ",", sizeof(use_obj_names) - strlen(use_obj_names) - 1);
        strncat(use_obj_names, name, sizeof(use_obj_names) - strlen(use_obj_names) - 1);
    }
}

const char *stub_use_obj_seen_names(void) { return use_obj_names; }

int stub_use_obj_saw(const char *name)
{
    size_t n, i;
    if (name == NULL)
        return 0;
    n = strlen(use_obj_names);
    for (i = 0; i + strlen(name) <= n; i++) {
        if (strncmp(use_obj_names + i, name, strlen(name)) == 0)
            return 1;
    }
    return 0;
}

/* --- rsyslog core service: r_dbgprintf() (runtime/debug.c) ---
 * The dbgprintf() macro of the modules funnels into this function. */
void r_dbgprintf(const char *srcname, const char *fmt, ...)
{
    va_list ap;
    char line[1024];

    (void)srcname;
    stub_dbgprintf_calls++;
    va_start(ap, fmt);
    vsnprintf(line, sizeof(line), (fmt != NULL) ? fmt : "", ap);
    va_end(ap);
    if (strlen(stub_dbgprintf_log) + strlen(line) + 2 < sizeof(stub_dbgprintf_log)) {
        strncat(stub_dbgprintf_log, line,
                sizeof(stub_dbgprintf_log) - strlen(stub_dbgprintf_log) - 1);
    }
}

/* --- rsyslog core services: msg field setters (runtime/msg.c) ---
 * Signatures mirror runtime/msg.h:180-202; the module hands its own smsg_t*
 * which the shim does not dereference (it only records the payload). */
void MsgSetTAG(void *pMsg, const unsigned char *pszBuf, size_t lenBuf)
{
    size_t n;
    (void)pMsg;
    stub_msgsettag_calls++;
    stub_msgsettag_lastlen = (int)lenBuf;
    if (pszBuf != NULL) {
        n = lenBuf < sizeof(stub_msgsettag_last) - 1 ? lenBuf : sizeof(stub_msgsettag_last) - 1;
        memcpy(stub_msgsettag_last, pszBuf, n);
        stub_msgsettag_last[n] = '\0';
    }
}

void MsgSetHOSTNAME(void *pMsg, const unsigned char *pszHOSTNAME, int lenHOSTNAME)
{
    size_t n;
    (void)pMsg;
    stub_msgsethostname_calls++;
    stub_msgsethostname_lastlen = lenHOSTNAME;
    if (pszHOSTNAME != NULL && lenHOSTNAME > 0) {
        n = (size_t)lenHOSTNAME;
        if (n > sizeof(stub_msgsethostname_last) - 1)
            n = sizeof(stub_msgsethostname_last) - 1;
        memcpy(stub_msgsethostname_last, pszHOSTNAME, n);
        stub_msgsethostname_last[n] = '\0';
    }
}

void MsgSetMSGoffs(void *pMsg, int offs)
{
    (void)pMsg;
    stub_msgsetmsgoffs_calls++;
    stub_msgsetmsgoffs_last = offs;
}

void setProtocolVersion(void *pMsg, int iNewVersion)
{
    (void)pMsg;
    stub_setprotocolversion_calls++;
    stub_setprotocolversion_last = iNewVersion;
}

void applyDfltTZ(void *pTime, char *tz)
{
    (void)pTime;
    (void)tz;
    stub_applydflttz_calls++;
}

/* --- rsyslog core services: config parameter handling ---
 * Reached only when newParserInst() is called with a parameter block; the
 * end-to-end test passes lst == NULL (the module then keeps its defaults), so
 * these exist for RTLD_NOW resolution and are asserted not to be needed. */
void *nvlstGetParams(void *lst, void *pblk, void *pvals)
{
    (void)lst;
    (void)pblk;
    (void)pvals;
    return NULL;
}

void cnfparamsPrint(void *pblk, void *pvals)
{
    (void)pblk;
    (void)pvals;
}

void cnfparamvalsDestruct(void *pvals, void *pblk)
{
    (void)pvals;
    (void)pblk;
}

/* --- host callback: objGetObjInterface (runtime/module-template.h) ---
 * modInit() asks for the object subsystem interface and then uses
 * obj.UseObj()/obj.ReleaseObj() to acquire glbl/datetime/parser, so the shim
 * must present a *callable* interface — the field offsets are the ABI facts of
 * runtime/obj-types.h (ifBEGIN at 0: ifVersion/ifIsLoaded). */
int stub_obj_get_obj_interface(void *pIf)
{
    unsigned char *b = (unsigned char *)pIf;

    stub_obj_iface_calls++;
    if (b == NULL)
        return STUB_RS_RET_PARAM_ERROR;
    memset(b, 0, STUB_OBJIF_SIZE);
    *(int *)(b + STUB_OBJIF_OFF_IFVERSION) = STUB_OBJ_CURR_IF_VERSION;
    *(int *)(b + STUB_OBJIF_OFF_IFISLOADED) = 1;
    *(void **)(b + STUB_OBJIF_OFF_USEOBJ) = (void *)stub_use_obj;
    *(void **)(b + STUB_OBJIF_OFF_RELEASEOBJ) = (void *)stub_release_obj;
    return STUB_RS_RET_OK;
}

/* --- host callback: regCfSysLineHdlr (runtime/module-template.h) ---
 * Neither parser module registers a config variable (no omsdRegCFSLineHdlr in
 * their sources), but CODEmodInit_QueryRegCFSLineHdlr still resolves the
 * callback, so it is provided and its (zero) use is asserted. */
int stub_reg_cfs_line_hdlr(unsigned char *pCmdName, int bChainingPermitted,
                           int eType, int (*pHdlr)(void), void *pData,
                           void *pOwnerCookie)
{
    (void)pCmdName;
    (void)bChainingPermitted;
    (void)eType;
    (void)pHdlr;
    (void)pData;
    (void)pOwnerCookie;
    stub_reg_cfs_calls++;
    return STUB_RS_RET_OK;
}

/* --- datetime_if_t.ParseTIMESTAMP3164 (runtime/datetime.h:43) ---
 * pmciscoios hands each message to this host service and relies on the cursor
 * being advanced past the timestamp. The shim accepts exactly the RFC3164 shape
 * the module feeds it ("Mmm DD HH:MM:SS", spaces at 3/6/15, colons at 9/12),
 * consumes the ": " separator the real parser strips (see the module's comment
 * at pmciscoios.c:207) and advances the cursor by 18 characters. If the cursor
 * the module passes is not a valid timestamp the call fails like the real
 * parser would, which makes the test's positive case self-checking. */
static int stub_dt_ParseTIMESTAMP3164(void *pTime, unsigned char **ppszTS, int *pLen,
                                      int bParseTZ, int bPermitYear)
{
    unsigned char *p;
    int ret;

    (void)pTime;
    (void)bParseTZ;
    (void)bPermitYear;
    stub_dt_parse_calls++;
    if (ppszTS == NULL || *ppszTS == NULL || pLen == NULL) {
        stub_dt_parse_last_ret = STUB_RS_RET_PARAM_ERROR;
        return STUB_RS_RET_PARAM_ERROR;
    }
    p = *ppszTS;
    stub_dt_parse_last_len = *pLen;
    snprintf(stub_dt_parse_last, sizeof(stub_dt_parse_last), "%.48s", (const char *)p);
    /* the real core parser consumes the 15-char "Jan  1 00:00:00" plus the
     * ": " that follows it (pmciscoios.c:207 notes the parser strips it) */
    if (stub_dt_parse_forced_fail || p[3] != ' ' || p[6] != ' ' || p[9] != ':' ||
        p[12] != ':' || p[15] != ':' || p[16] != ' ' || *pLen < 17) {
        ret = STUB_RS_RET_COULD_NOT_PARSE;
    } else {
        *ppszTS += 17;
        *pLen -= 17;
        ret = STUB_RS_RET_OK;
    }
    stub_dt_parse_last_ret = ret;
    return ret;
}

/* --- glbl_if_t.GetParseHOSTNAMEandTAG (runtime/glbl.h) ---
 * pmcisconames caches this global in modInit(); the shim returns the rsyslogd
 * default (1: hostnames and tags are parsed by the core) and records the call
 * so the test proves modInit() really reached it with loadConf. */
static int stub_glbl_GetParseHOSTNAMEandTAG(void *pConf)
{
    (void)pConf;
    stub_glbl_parsehostname_calls++;
    return stub_glbl_parsehostname_ret;
}

/* --- obj.UseObj() / obj.ReleaseObj() (runtime/obj-types.h:398-399) ---
 * objUse(glbl|parser|datetime, CORE_COMPONENT) lands here with the module's own
 * static interface struct; the shim fills it with the object's real entry
 * points at the offsets the module was compiled against. */
int stub_use_obj(const char *srcFile, unsigned char *objName, unsigned char *fileName, void *pIf)
{
    const char *n = (const char *)objName;
    unsigned char *b = (unsigned char *)pIf;

    (void)srcFile;
    (void)fileName;
    stub_use_obj_calls++;
    if (n != NULL)
        stub_seen_add(n);
    if (b == NULL)
        return STUB_RS_RET_PARAM_ERROR;
    if (n != NULL && strcmp(n, "datetime") == 0) {
        memset(b, 0, STUB_DTIF_SIZE);
        *(int *)(b + 0) = STUB_DT_CURR_IF_VERSION;
        *(int *)(b + STUB_DTIF_OFF_IFISLOADED) = 1;
        *(void **)(b + STUB_DTIF_OFF_PARSETIMESTAMP3164) = (void *)stub_dt_ParseTIMESTAMP3164;
        return STUB_RS_RET_OK;
    }
    if (n != NULL && strcmp(n, "glbl") == 0) {
        memset(b, 0, STUB_GLBLIF_SIZE);
        *(int *)(b + 0) = STUB_GLBL_CURR_IF_VERSION;
        *(int *)(b + STUB_GLBLIF_OFF_IFISLOADED) = 1;
        *(void **)(b + STUB_GLBLIF_OFF_GETPARSEHOSTNAMEANDTAG) =
            (void *)stub_glbl_GetParseHOSTNAMEandTAG;
        return STUB_RS_RET_OK;
    }
    if (n != NULL && strcmp(n, "parser") == 0) {
        /* only acquired/released by the modules; no entry point is called */
        memset(b, 0, STUB_OBJIF_SIZE);
        *(int *)(b + STUB_OBJIF_OFF_IFISLOADED) = 1;
        return STUB_RS_RET_OK;
    }
    return STUB_RS_RET_OK;
}

int stub_release_obj(const char *srcFile, unsigned char *objName, unsigned char *fileName,
                     void *pIf)
{
    (void)srcFile;
    (void)objName;
    (void)fileName;
    (void)pIf;
    stub_release_obj_calls++;
    return STUB_RS_RET_OK;
}

/* --- host query callback handed to modInit() --- */
int stub_host_query(unsigned char *name, void (**ppFn)(void))
{
    const char *n = (const char *)name;

    stub_host_query_calls++;
    if (ppFn == NULL || n == NULL)
        return STUB_RS_RET_PARAM_ERROR;
    *ppFn = NULL;
    if (strcmp(n, "objGetObjInterface") == 0) {
        *ppFn = (void (*)(void))stub_obj_get_obj_interface;
        return STUB_RS_RET_OK;
    }
    if (strcmp(n, "regCfSysLineHdlr") == 0) {
        *ppFn = (void (*)(void))stub_reg_cfs_line_hdlr;
        return STUB_RS_RET_OK;
    }
    return STUB_RS_RET_NOT_FOUND;
}
