#include <expat.h>
#include <dlfcn.h>
#include <stdio.h>

#ifndef TARGET_SO
#define TARGET_SO "libexpat.so"
#endif

typedef XML_Parser (*XML_ParserCreateFunc)(const XML_Char *);
typedef enum XML_Status (*XML_ParseFunc)(XML_Parser, const char *, int, int);
typedef void (*XML_ParserFreeFunc)(XML_Parser);

static void *load_symbol(void *handle, const char *name) {
    dlerror();
    void *symbol = dlsym(handle, name);
    const char *error = dlerror();
    if (error || !symbol) {
        fprintf(stderr, "missing expat API symbol %s: %s\n", name, error ? error : "unknown error");
        return NULL;
    }
    return symbol;
}

int main(void) {
#ifdef TEST_STATIC
    void *h = NULL;
    XML_ParserCreateFunc create_parser = XML_ParserCreate;
    XML_ParseFunc parse = XML_Parse;
    XML_ParserFreeFunc free_parser = XML_ParserFree;
#else
    /* Force a direct symbol reference so the shared consumer really links
       against the installed Expat library, not only libdl. */
    if (!XML_ExpatVersion() || !*XML_ExpatVersion()) {
        fprintf(stderr, "XML_ExpatVersion failed\n");
        return 1;
    }
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        const char *error = dlerror();
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, error ? error : "unknown error");
        return 1;
    }

    XML_ParserCreateFunc create_parser = (XML_ParserCreateFunc)load_symbol(h, "XML_ParserCreate");
    XML_ParseFunc parse = (XML_ParseFunc)load_symbol(h, "XML_Parse");
    XML_ParserFreeFunc free_parser = (XML_ParserFreeFunc)load_symbol(h, "XML_ParserFree");
#endif
    if (!create_parser || !parse || !free_parser) {
        if (h) dlclose(h);
        return 1;
    }

    XML_Parser parser = create_parser(NULL);
    if (!parser) {
        fprintf(stderr, "XML_ParserCreate failed\n");
        if (h) dlclose(h);
        return 1;
    }

    const char xml[] = "<root><child>ok</child></root>";
    if (parse(parser, xml, (int)(sizeof(xml) - 1), 1) != XML_STATUS_OK) {
        fprintf(stderr, "XML_Parse failed\n");
        free_parser(parser);
        if (h) dlclose(h);
        return 1;
    }

    free_parser(parser);
#ifdef TEST_STATIC
    printf("expat: static link and parse ok\n");
#else
    printf("expat: dlopen %s and parse ok\n", TARGET_SO);
#endif
    if (h) dlclose(h);
    return 0;
}
