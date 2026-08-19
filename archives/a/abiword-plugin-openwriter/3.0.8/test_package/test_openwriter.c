/* test_openwriter.c — abiword-plugin-openwriter test_package runtime test.
 *
 * R34 (libgsf API surface) check: links against libgsf-1 + libglib-2.0 via
 * PkgConfig::LIBGSF / PkgConfig::GLIB IMPORTED targets, then runs a real
 * libgsf round-trip:
 *
 *   write path:
 *     gsf_output_stdio_new       (open /tmp/test_openwriter_*.zip)
 *     gsf_outfile_zip_new        (create zip archive rooted at sink)
 *     gsf_outfile_new_child      (add marker.txt to archive)
 *     gsf_output_write           (write "hello" into marker.txt)
 *     gsf_output_close           (finalize zip)
 *
 *   read path:
 *     gsf_input_stdio_new        (open /tmp zip we just wrote)
 *     gsf_input_uncompress       (decompress if gzipped)
 *     gsf_infile_zip_new         (parse zip root)
 *     gsf_infile_num_children /
 *     gsf_infile_child_by_index  (enumerate + verify marker.txt)
 *
 * The archive has no real abiword content — openwriter's job is to *render*
 * abiword docs into ODF. We only prove libgsf's ZIP output/read machinery is
 * callable from this binary.
 *
 * openwriter.so is an *abiword plugin*: it is dlopen'd by the abiword
 * process at runtime, which provides the IE_Exp / PD_Document /
 * UT_String / ... symbol pool. We deliberately do NOT dlopen openwriter.so
 * from this test binary — there is no libabiword recipe at this CI gate,
 * and the musl dynamic loader on the OHOS HNP sandbox would reject
 * openwriter.so on load anyway (the .so has 130+ abiword-internal
 * undefined symbols that only the abiword host process resolves).
 *
 * Per R-NEW 2026-08-10 / Phase 2.3, the cross-compiled (OHOS/ARM64)
 * binary is smoke-tested via qemu-aarch64 outside this CI gate; this
 * test runs natively on the worker.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <glib.h>
#include <gsf/gsf.h>
#include <gsf/gsf-utils.h>
#include <gsf/gsf-output-stdio.h>
#include <gsf/gsf-outfile.h>
#include <gsf/gsf-outfile-zip.h>
#include <gsf/gsf-input-stdio.h>
#include <gsf/gsf-input-gzip.h>
#include <gsf/gsf-infile.h>
#include <gsf/gsf-infile-zip.h>

int main(void) {
    char tmpl[] = "/tmp/test_openwriter_XXXXXX";
    int fd = mkstemp(tmpl);
    if (fd < 0) { perror("mkstemp"); return 1; }
    close(fd);

    gsf_init();

    /* ---------- write path ---------- */
    GError *err = NULL;
    GsfOutput *sink = gsf_output_stdio_new(tmpl, &err);
    if (!sink) {
        fprintf(stderr, "gsf_output_stdio_new failed: %s\n",
                err ? err->message : "(no error)");
        if (err) g_error_free(err);
        unlink(tmpl);
        gsf_shutdown();
        return 2;
    }
    GsfOutfile *zip = gsf_outfile_zip_new(sink, &err);
    if (!zip) {
        fprintf(stderr, "gsf_outfile_zip_new failed: %s\n",
                err ? err->message : "(no error)");
        if (err) g_error_free(err);
        g_object_unref(sink);
        unlink(tmpl);
        gsf_shutdown();
        return 3;
    }
    GsfOutput *child = gsf_outfile_new_child(zip, "marker.txt", FALSE);
    if (!child) {
        fprintf(stderr, "gsf_outfile_new_child failed\n");
        g_object_unref(zip); /* also unrefs sink */
        unlink(tmpl);
        gsf_shutdown();
        return 4;
    }
    const char payload[] = "hello";
    if (gsf_output_write(child, sizeof(payload) - 1, payload) == FALSE) {
        fprintf(stderr, "gsf_output_write failed\n");
        g_object_unref(child);
        g_object_unref(zip);
        unlink(tmpl);
        gsf_shutdown();
        return 5;
    }
    gsf_output_close(child);
    g_object_unref(child);
    gsf_output_close(GSF_OUTPUT(zip));
    g_object_unref(zip); /* also unrefs sink */

    /* ---------- read path ---------- */
    err = NULL;
    GsfInput *source = gsf_input_stdio_new(tmpl, &err);
    if (!source) {
        fprintf(stderr, "gsf_input_stdio_new failed: %s\n",
                err ? err->message : "(no error)");
        if (err) g_error_free(err);
        unlink(tmpl);
        gsf_shutdown();
        return 6;
    }
    source = gsf_input_uncompress(source);
    GsfInfile *infile = gsf_infile_zip_new(source, &err);
    g_object_unref(source); /* infile holds its own ref */
    if (!infile) {
        fprintf(stderr, "gsf_infile_zip_new failed: %s\n",
                err ? err->message : "(no error)");
        if (err) g_error_free(err);
        unlink(tmpl);
        gsf_shutdown();
        return 7;
    }
    gboolean found = FALSE;
    int n = gsf_infile_num_children(infile);
    for (int i = 0; i < n; i++) {
        GsfInput *kid = gsf_infile_child_by_index(infile, i);
        if (kid == NULL) continue;
        const char *name = gsf_input_name(kid);
        if (name && strcmp(name, "marker.txt") == 0) {
            found = TRUE;
        }
        g_object_unref(kid);
    }
    g_object_unref(infile);
    unlink(tmpl);
    gsf_shutdown();

    if (!found) {
        fprintf(stderr, "marker.txt not found in produced zip\n");
        return 8;
    }
    printf("test_openwriter: libgsf API round-trip OK (zip written+read)\n");
    fflush(stdout);
    return 0;
}