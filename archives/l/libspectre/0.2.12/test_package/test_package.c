#include <libspectre/spectre.h>

#include <stdio.h>
#include <stdlib.h>

static int
write_postscript(const char *path)
{
    FILE *file = fopen(path, "w");
    if (file == NULL)
        return 0;

    fputs("%!PS-Adobe-3.0\n"
          "%%Pages: 1\n"
          "%%BoundingBox: 0 0 100 100\n"
          "%%Page: 1 1\n"
          "newpath 10 10 moveto 90 90 lineto 2 setlinewidth stroke\n"
          "showpage\n%%EOF\n", file);
    return fclose(file) == 0;
}

int
main(void)
{
    const char *path = "libspectre-harmonyos-smoke.ps";
    SpectreDocument *document;
    SpectrePage *page;
    SpectreRenderContext *context;
    unsigned char *pixels = NULL;
    int row_length = 0;
    int width = 0;
    int height = 0;
    int failed = 0;
    int passed = 0;

    if (!write_postscript(path)) {
        fprintf(stderr, "cannot create PostScript smoke document\n");
        return 1;
    }

    document = spectre_document_new();
    spectre_document_load(document, path);
    if (spectre_document_status(document) != SPECTRE_STATUS_SUCCESS) {
        fprintf(stderr, "document load failed: %s\n",
                spectre_status_to_string(spectre_document_status(document)));
        failed = 1;
        goto done;
    }
    puts("PASS 1/4: PostScript document loaded");
    ++passed;
    if (spectre_document_get_n_pages(document) != 1) {
        fprintf(stderr, "expected one page, got %u\n",
                spectre_document_get_n_pages(document));
        failed = 1;
        goto done;
    }
    puts("PASS 2/4: document has one page");
    ++passed;

    spectre_document_get_page_size(document, &width, &height);
    if (width <= 0 || height <= 0) {
        fprintf(stderr, "invalid page size: %d x %d\n", width, height);
        failed = 1;
        goto done;
    }
    puts("PASS 3/4: page dimensions are positive");
    ++passed;

    page = spectre_document_get_page(document, 0);
    context = spectre_render_context_new();
    spectre_page_render(page, context, &pixels, &row_length);
    if (spectre_page_status(page) != SPECTRE_STATUS_SUCCESS ||
        pixels == NULL || row_length <= 0) {
        fprintf(stderr, "Ghostscript page rendering failed\n");
        failed = 1;
    } else {
        puts("PASS 4/4: Ghostscript rendered a pixel buffer");
        ++passed;
    }
    free(pixels);
    spectre_render_context_free(context);
    spectre_page_free(page);

done:
    spectre_document_free(document);
    remove(path);
    printf("HARMONYOS_TESTS=%d/4\n", passed);
    if (!failed && passed == 4)
        puts("HarmonyOS PostScript load, metadata and Ghostscript render: PASS");
    return failed;
}
