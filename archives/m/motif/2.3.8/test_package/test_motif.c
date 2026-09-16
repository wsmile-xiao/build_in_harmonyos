/*
 * motif 2.3.8 Conan test_package — R34 substantive consumer test.
 *
 * (1) Links against the packaged libXm.so.4 and exercises the XmString API the
 *     dinotrace consumer needs. NOTE: XmStringLength() returns the compound
 *     string's BYTE length, not the character count (XmStringLength of "Hello"
 *     is 14 for an LtoR compound string), so we only assert a RELATION
 *     (length(concat) > length(a) and > length(b)) and never a character count.
 * (2) dlopen()s the packaged SONAME libXm.so.4 with RTLD_NOW and resolves the
 *     entry points dinotrace imports, reporting each as OK / MISSING.
 *
 * Prints `assertions=N failures=0` and exits non-zero on any failure.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <Xm/Xm.h>

static int assertions = 0;
static int failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        assertions++;                                                          \
        if (!(cond)) {                                                         \
            fprintf(stderr, "FAIL: %s\n", (msg));                              \
            failures++;                                                        \
        }                                                                      \
    } while (0)

static const char *const entry_points[] = {
    "XmCreateForm",
    "XmCreateMainWindow",
    "XmCreateDrawingArea",
    "XmCreateScrollBar",
    "XmCreateText",
    "XmStringCreateLtoR",
    "XtAppInitialize",
};

int main(void) {
    XmString a, b, c, empty;
    char *text = NULL;

    /* --- (1) linked XmString API assertions --- */
    a = XmStringCreateLtoR("Hello", XmFONTLIST_DEFAULT_TAG);
    CHECK(a != NULL, "XmStringCreateLtoR(\"Hello\") != NULL");

    b = XmStringCreateSimple("World");
    CHECK(b != NULL, "XmStringCreateSimple(\"World\") != NULL");

    c = XmStringConcat(a, b);
    CHECK(c != NULL, "XmStringConcat(a, b) != NULL");

    CHECK(XmStringCompare(a, a) == 1, "XmStringCompare(a, a) == 1");
    CHECK(XmStringCompare(a, b) != 1, "XmStringCompare(a, b) != 1");

    CHECK(XmStringGetLtoR(a, XmFONTLIST_DEFAULT_TAG, &text) &&
              text != NULL && strcmp(text, "Hello") == 0,
          "XmStringGetLtoR(a) == \"Hello\"");

    empty = XmStringCreateSimple("");
    CHECK(XmStringEmpty(empty) == 1, "XmStringEmpty(XmStringCreateSimple(\"\")) == 1");

    CHECK(XmStringHasSubstring(c, a) == 1, "XmStringHasSubstring(concat, a) == 1");
    CHECK(XmStringByteCompare(a, a) == 1, "XmStringByteCompare(a, a) == 1");
    /* XmStringLength() returns the compound string BYTE length (incl. layout/tag
       overhead), not a character count: measured len("Hello")=14, len("World")=18,
       len(concat)=31 -- so concat is NOT the exact sum. Assert the robust relation. */
    CHECK(XmStringLength(c) > XmStringLength(a) && XmStringLength(c) > XmStringLength(b),
          "XmStringLength(concat) > XmStringLength(a) and > XmStringLength(b)");

    /* --- (2) dlopen the packaged SONAME and resolve consumer entry points --- */
    {
        void *handle = dlopen("libXm.so.4", RTLD_NOW);
        CHECK(handle != NULL, "dlopen(\"libXm.so.4\", RTLD_NOW) != NULL");
        if (handle == NULL) {
            fprintf(stderr, "  dlopen error: %s\n", dlerror());
        } else {
            size_t i;
            for (i = 0; i < sizeof(entry_points) / sizeof(entry_points[0]); ++i) {
                void *sym = dlsym(handle, entry_points[i]);
                if (sym != NULL) {
                    printf("dlopen symbol %-22s : OK\n", entry_points[i]);
                } else {
                    printf("dlopen symbol %-22s : MISSING\n", entry_points[i]);
                }
                assertions++;
                if (sym == NULL) {
                    failures++;
                }
            }
            dlclose(handle);
        }
    }

    /* --- cleanup --- */
    XmStringFree(a);
    XmStringFree(b);
    XmStringFree(c);
    XmStringFree(empty);
    if (text != NULL) {
        XtFree(text);
    }

    printf("assertions=%d failures=%d\n", assertions, failures);
    return failures ? 1 : 0;
}
