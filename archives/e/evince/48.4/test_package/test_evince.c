#include <evince-document.h>
#include <glib.h>
#include <stdio.h>

int main(void) {
    /* 触发 GType 注册，验证 libevdocument3 ABI 可解析（无需 GTK/显示环境） */
    GType doc_type = ev_document_get_type();
    EvDocument *doc = ev_document_factory_get_document(NULL, NULL);

    g_print("ev_document type=%s\n", g_type_name(doc_type));

    if (!G_TYPE_IS_OBJECT(doc_type)) {
        g_printerr("ABI mismatch: unexpected GType kind\n");
        return 1;
    }
    if (doc != NULL) {
        g_printerr("expected NULL document for NULL uri, got %p\n", (void *)doc);
        g_object_unref(doc);
        return 1;
    }

    return 0;
}
