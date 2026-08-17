#include <libxslt/xsltconfig.h>
#include <libxslt/xslt.h>
#include <libxslt/xsltutils.h>
#include <libxslt/transform.h>
#include <stdio.h>

typedef struct {
    xsltHandleDebuggerCallback handler;
    xsltAddCallCallback add;
    xsltDropCallCallback drop;
} ProbeDebuggerCallbacks;

static int handler_calls = 0;
static int add_calls = 0;
static int drop_calls = 0;

static void probe_handler(xmlNodePtr cur, xmlNodePtr node, xsltTemplatePtr templ, xsltTransformContextPtr ctxt) {
    (void)cur;
    (void)node;
    (void)templ;
    (void)ctxt;
    handler_calls++;
}

static int probe_add(xsltTemplatePtr templ, xmlNodePtr source) {
    (void)templ;
    (void)source;
    add_calls++;
    return 1;
}

static void probe_drop(void) {
    drop_calls++;
}

int main(void) {
    ProbeDebuggerCallbacks callbacks = {probe_handler, probe_add, probe_drop};
    ProbeDebuggerCallbacks empty_callbacks = {NULL, NULL, NULL};

    if (LIBXSLT_VERSION < 10145) {
        fprintf(stderr, "unexpected libxslt version: %d\n", LIBXSLT_VERSION);
        return 1;
    }
    if (xsltLibxsltVersion < 10145) {
        fprintf(stderr, "unexpected libxslt runtime version: %d\n", xsltLibxsltVersion);
        return 1;
    }
#ifndef WITH_DEBUGGER
    fprintf(stderr, "libxslt debugger support is not enabled\n");
    return 1;
#else
    xsltSetDebuggerStatus(XSLT_DEBUG_STEP);
    if (xsltGetDebuggerStatus() != XSLT_DEBUG_STEP) {
        fprintf(stderr, "debugger status round-trip failed\n");
        return 1;
    }
    if (xsltSetDebuggerCallbacks(3, &callbacks) != 0) {
        fprintf(stderr, "debugger callback registration failed\n");
        return 1;
    }
    xslHandleDebugger(NULL, NULL, NULL, NULL);
    if (handler_calls != 1) {
        fprintf(stderr, "debugger handler callback was not invoked\n");
        return 1;
    }
    if (xslAddCall(NULL, NULL) != 1 || add_calls != 1) {
        fprintf(stderr, "debugger add callback was not invoked\n");
        return 1;
    }
    xslDropCall();
    if (drop_calls != 1) {
        fprintf(stderr, "debugger drop callback was not invoked\n");
        return 1;
    }
    if (xsltSetDebuggerCallbacks(3, &empty_callbacks) != 0) {
        fprintf(stderr, "debugger callback reset failed\n");
        return 1;
    }
    xsltSetDebuggerStatus(XSLT_DEBUG_NONE);
#endif
    xsltInit();
    xsltCleanupGlobals();
    printf("libxslt debugger probe ok: %d\n", xsltLibxsltVersion);
    return 0;
}
