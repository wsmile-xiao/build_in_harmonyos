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
    void *h = dlopen(TARGET_SO, RTLD_NOW | RTLD_GLOBAL);
    if (!h) {
        const char *error = dlerror();
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, error ? error : "unknown error");
        return 1;
    }

    XML_ParserCreateFunc create_parser = (XML_ParserCreateFunc)load_symbol(h, "XML_ParserCreate");
    XML_ParseFunc parse = (XML_ParseFunc)load_symbol(h, "XML_Parse");
    XML_ParserFreeFunc free_parser = (XML_ParserFreeFunc)load_symbol(h, "XML_ParserFree");
    if (!create_parser || !parse || !free_parser) {
        dlclose(h);
        return 1;
    }

    XML_Parser parser = create_parser(NULL);
    if (!parser) {
        fprintf(stderr, "XML_ParserCreate failed\n");
        dlclose(h);
        return 1;
    }

    const char xml[] = "<root><child>ok</child></root>";
    if (parse(parser, xml, (int)(sizeof(xml) - 1), 1) != XML_STATUS_OK) {
        fprintf(stderr, "XML_Parse failed\n");
        free_parser(parser);
        dlclose(h);
        return 1;
    }

    free_parser(parser);
    printf("expat: dlopen %s ok\n", TARGET_SO);
    dlclose(h);
    return 0;
}
