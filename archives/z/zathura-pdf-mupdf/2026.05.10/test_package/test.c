/* test.c — verify zathura-pdf-mupdf plugin from a consumer perspective.
 *
 * A zathura plugin is a dlopen object: it embeds MuPDF statically, pulls
 * girara/cairo via DT_NEEDED, and resolves the zathura_* host API from the
 * process that loads it. This test plays the host role: it exports minimal
 * zathura_* stubs (compiled with -rdynamic) so the plugin's relocations
 * bind, then validates the exported plugin definition
 * (zathura_plugin_<API>_<ABI>): name, version and mimetype table.
 * The plugin's internal functions are hidden (gnu_symbol_visibility), so
 * the definition struct is the only ABI surface — exactly what zathura
 * itself probes when loading plugins.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stddef.h>
#include <string.h>

#ifndef TARGET_SO
#define TARGET_SO "libpdf-mupdf.so"
#endif

/* ── zathura host API stubs (never executed; exist for relocation) ── */
const char* zathura_document_get_path(void* document) { (void)document; return 0; }
const char* zathura_document_get_password(void* document) { (void)document; return 0; }
void* zathura_document_get_data(void* document) { (void)document; return 0; }
void zathura_document_set_data(void* document, void* data) { (void)document; (void)data; }
void zathura_document_set_number_of_pages(void* document, unsigned int pages) { (void)document; (void)pages; }
void* zathura_document_information_entry_list_new(void) { return 0; }
void* zathura_document_information_entry_new(const char* name, void* value) { (void)name; (void)value; return 0; }
void* zathura_index_element_new(const char* title) { (void)title; return 0; }
void* zathura_link_new(int type) { (void)type; return 0; }
void zathura_link_free(void* link) { (void)link; }
void* zathura_page_get_document(void* page) { (void)page; return 0; }
unsigned int zathura_page_get_index(void* page) { (void)page; return 0; }
double zathura_page_get_width(void* page) { (void)page; return 0; }
double zathura_page_get_height(void* page) { (void)page; return 0; }
void zathura_page_set_data(void* page, void* data) { (void)page; (void)data; }
void zathura_page_set_width(void* page, double width) { (void)page; (void)width; }
void zathura_page_set_height(void* page, double height) { (void)page; (void)height; }

/* ── mirror of zathura/plugin-api.h (API 6 / ABI 7, zathura 2026.05.20) ── */
typedef struct {
    unsigned int major;
    unsigned int minor;
    unsigned int rev;
} zathura_plugin_version_t;

typedef struct {
    const void* document_open;
    const void* document_free;
    const void* document_index_generate;
    const void* document_save_as;
    const void* document_attachments_get;
    const void* document_attachment_save;
    const void* document_get_information;
    const void* page_init;
    const void* page_clear;
    const void* page_search_text;
    const void* page_links_get;
    const void* page_form_fields_get;
    const void* page_images_get;
    const void* page_image_get_cairo;
    const void* page_get_text;
    const void* page_get_selection;
    const void* page_render_cairo;
    const void* page_get_label;
    const void* page_get_signatures;
} zathura_plugin_functions_t;

typedef struct {
    const char* name;
    const zathura_plugin_version_t version;
    const zathura_plugin_functions_t functions;
    const size_t mime_types_size;
    const char** mime_types;
} zathura_plugin_definition_t;

int main(void) {
    void* h = dlopen(TARGET_SO, RTLD_NOW | RTLD_LOCAL);
    if (!h) {
        fprintf(stderr, "dlopen %s failed: %s\n", TARGET_SO, dlerror());
        return 1;
    }
    printf("zathura-pdf-mupdf: dlopen %s ok (host API relocations bound)\n", TARGET_SO);

    zathura_plugin_definition_t* def =
        (zathura_plugin_definition_t*)dlsym(h, "zathura_plugin_6_7");
    if (!def) {
        fprintf(stderr, "dlsym zathura_plugin_6_7 failed: %s\n", dlerror());
        dlclose(h);
        return 1;
    }

    if (!def->name || strcmp(def->name, "pdf-mupdf") != 0) {
        fprintf(stderr, "unexpected plugin name: %s\n", def->name ? def->name : "()");
        dlclose(h);
        return 1;
    }
    printf("zathura-pdf-mupdf: plugin %s, plugin version %u.%u.%u\n",
           def->name, def->version.major, def->version.minor, def->version.rev);

    if (def->mime_types_size == 0 || def->mime_types_size > 64 || !def->mime_types) {
        fprintf(stderr, "implausible mime_types_size: %zu\n", (size_t)def->mime_types_size);
        dlclose(h);
        return 1;
    }
    int has_pdf = 0;
    for (size_t i = 0; i < def->mime_types_size; ++i) {
        if (def->mime_types[i] && strcmp(def->mime_types[i], "application/pdf") == 0) {
            has_pdf = 1;
            break;
        }
    }
    if (!has_pdf) {
        fprintf(stderr, "application/pdf mimetype missing from plugin\n");
        dlclose(h);
        return 1;
    }
    printf("zathura-pdf-mupdf: plugin ABI verified (%zu mimetypes, application/pdf supported)\n",
           (size_t)def->mime_types_size);

    dlclose(h);
    return 0;
}
