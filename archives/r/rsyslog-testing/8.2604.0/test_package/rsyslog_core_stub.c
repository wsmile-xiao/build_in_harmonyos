/* rsyslog_core_stub.c — see rsyslog_core_stub.h for the rationale.
 *
 * The symbols defined here are intentionally *exported* (the test binary is
 * linked with -Wl,--export-dynamic) so that dlopen(RTLD_NOW) of omtesting.so
 * resolves the module's imports against this shim instead of rsyslogd.
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "rsyslog_core_stub.h"

int stub_host_query_calls = 0;
int stub_obj_iface_calls = 0;
int stub_reg_cfs_calls = 0;
int stub_dbgprintf_calls = 0;
int stub_omsr_construct_calls = 0;
int stub_omsr_destruct_calls = 0;
int stub_omsr_last_num_entries = 0;
int stub_cfline_calls = 0;
int stub_random_calls = 0;

char stub_reg_cfs_lastname[64] = {0};
int stub_reg_cfs_lasttype = 0;
int stub_reg_cfs_handler_present = 0;
int stub_reg_cfs_last_chain = -1;
void *stub_reg_cfs_last_data = NULL;
void *stub_reg_cfs_last_owner = NULL;

char stub_dbgprintf_log[8192] = {0};
static char seen_names[1024] = {0};

int stub_host_query_saw(const char *name)
{
    /* seen_names holds "name1,name2,..." */
    size_t n = strlen(seen_names);
    size_t i;
    for (i = 0; i + strlen(name) <= n; i++) {
        if (strncmp(seen_names + i, name, strlen(name)) == 0)
            return 1;
    }
    return 0;
}

const char *stub_host_query_seen_names(void) { return seen_names; }

static void stub_seen_add(const char *name)
{
    if (strlen(seen_names) + strlen(name) + 2 < sizeof(seen_names)) {
        if (seen_names[0] != '\0')
            strncat(seen_names, ",", sizeof(seen_names) - strlen(seen_names) - 1);
        strncat(seen_names, name, sizeof(seen_names) - strlen(seen_names) - 1);
    }
}

/* --- rsyslog core service: r_dbgprintf() (runtime/debug.c) ---
 * The dbgprintf() macro used by the module funnels into this function
 * (dbgprintf(...) -> r_dbgprintf(__FILE__, ...)); runtime/debug.h declares it as
 * void r_dbgprintf(const char *srcname, const char *fmt, ...). */
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

/* --- rsyslog core service: template object (runtime/objomsr.c) ---
 * Reached through parseSelectorAct(): module-template.h
 * CODE_STD_STRING_REQUESTparseSelectorAct expands to OMSRconstruct(ppOMSR, 1),
 * so the module hands the core a fresh request object. The shim allocates a real
 * opaque object (the module never dereferences it; it only forwards the pointer
 * to cflineParseTemplateName()) and records the requested entry count, which is
 * what the E2E asserts on. */
int OMSRconstruct(void **ppThis, int iNumEntries)
{
    stub_omsr_construct_calls++;
    stub_omsr_last_num_entries = iNumEntries;
    if (ppThis == NULL || iNumEntries < 1)
        return -207; /* RS_RET_PARAM_ERROR */
    *ppThis = calloc(1, sizeof(void *) * (size_t)(iNumEntries + 4));
    if (*ppThis == NULL)
        return -206; /* RS_RET_OUT_OF_MEMORY */
    return RS_RET_OK;
}

int OMSRdestruct(void *pThis)
{
    stub_omsr_destruct_calls++;
    free(pThis);
    return RS_RET_OK;
}

int cflineParseTemplateName(void *pline, void **ppOMSR, int bDoLock,
                            int iNumTpls, void *pDflt)
{
    (void)pline;
    (void)ppOMSR;
    (void)bDoLock;
    (void)iNumTpls;
    (void)pDflt;
    stub_cfline_calls++;
    return RS_RET_OK;
}

/* --- rsyslog core service: randomNumber() (runtime/srUtils.c) --- */
int randomNumber(void)
{
    stub_random_calls++;
    return 12345; /* deterministic: the randfail mode is not part of this test */
}

/* --- host query callback: what modInit() asks the host for --- */
int stub_host_query(unsigned char *name, void (**ppFn)(void))
{
    const char *n = (const char *)name;

    stub_host_query_calls++;
    if (n != NULL)
        stub_seen_add(n);
    if (ppFn == NULL || n == NULL)
        return -207; /* RS_RET_PARAM_ERROR */
    *ppFn = NULL;
    if (strcmp(n, "objGetObjInterface") == 0) {
        *ppFn = (void (*)(void))stub_obj_get_obj_interface;
        return RS_RET_OK;
    }
    if (strcmp(n, "regCfSysLineHdlr") == 0) {
        *ppFn = (void (*)(void))stub_reg_cfs_line_hdlr;
        return RS_RET_OK;
    }
    return RS_RET_STUB_NOT_FOUND;
}

/* --- host callback: objGetObjInterface (runtime/module-template.h) ---
 * modInit() only stores the returned interface into its own static obj; none
 * of the entry points exercised here dereference it. */
int stub_obj_get_obj_interface(void *pIf)
{
    stub_obj_iface_calls++;
    if (pIf == NULL)
        return -207; /* RS_RET_PARAM_ERROR */
    memset(pIf, 0, sizeof(void *) * 64); /* footprint >= sizeof(obj_if_t) */
    return RS_RET_OK;
}

/* --- host callback: regCfSysLineHdlr (runtime/module-template.h) ---
 * modInit() performs exactly one registration (omtesting.c:349):
 *   omsdRegCFSLineHdlr("actionomtestingechostdout", 0, eCmdHdlrBinary,
 *                      NULL, &cs.bEchoStdout, STD_LOADABLE_MODULE_ID)
 * i.e. a binary config variable -- handler is legitimately NULL, the variable is
 * passed via pData and the owner cookie is the module's own modExit pointer
 * (STD_LOADABLE_MODULE_ID, module-template.h:100). All of it is captured here so
 * the E2E can assert the *exact* registration the module made. */
int stub_reg_cfs_line_hdlr(unsigned char *pCmdName, int bChainingPermitted,
                           int eType, int (*pHdlr)(void), void *pData,
                           void *pOwnerCookie)
{
    stub_reg_cfs_calls++;
    stub_reg_cfs_lasttype = eType;
    stub_reg_cfs_handler_present = (pHdlr != NULL);
    stub_reg_cfs_last_chain = bChainingPermitted;
    stub_reg_cfs_last_data = pData;
    stub_reg_cfs_last_owner = pOwnerCookie;
    if (pCmdName != NULL) {
        snprintf(stub_reg_cfs_lastname, sizeof(stub_reg_cfs_lastname),
                 "%s", (const char *)pCmdName);
    }
    return RS_RET_OK;
}
