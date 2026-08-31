#include <cstring>

#include "clxclient.h"

/*
 * Exercise the packaged libclxclient through real, display-independent API:
 * X_resman parses an X resource database (Xrm*) without opening a display
 * connection, and X_callback exposes pure classification helpers. All calls
 * below resolve to non-inline symbols in libclxclient, so a missing export
 * fails at link time (R34).
 */

static XrmOptionDescRec g_options[] = {
    { (char *)"-geometry", (char *)"*geometry", XrmoptionSepArg, NULL },
    { (char *)"-title", (char *)"*title", XrmoptionSepArg, NULL },
};

int main(void)
{
    // A resource database built from the command line works without any
    // X display: XrmParseCommand feeds *geometry/*title, and get() reads
    // them straight back through the packaged library.
    X_resman resman;
    char *argv[] = {
        (char *)"clxtest",
        (char *)"-geometry", (char *)"1024x768",
        (char *)"-title", (char *)"Clxclient-Integration",
        NULL,
    };
    int argc = 5;
    resman.init(&argc, argv, (char *)"clxtest", g_options, 2);

    const char *geometry = resman.get(".geometry", "640x480");
    if (std::strcmp(geometry, "1024x768") != 0)
        return 2;
    const char *title = resman.get(".title", "unset");
    if (std::strcmp(title, "Clxclient-Integration") != 0)
        return 3;
    if (resman.getb(".mono", 1) != 1)
        return 4;

    return 0;
}
