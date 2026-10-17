#include <gio/gio.h>
#include <glib/gstdio.h>
#include <gnome-autoar/gnome-autoar.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    GFile *destination;
    GError *error;
    gboolean completed;
} ProbeState;

static void on_decide_destination(AutoarCompressor *compressor,
                                  GFile *destination,
                                  gpointer user_data) {
    ProbeState *state = user_data;
    (void)compressor;
    state->destination = g_object_ref(destination);
}

static void on_error(AutoarCompressor *compressor,
                     GError *error,
                     gpointer user_data) {
    ProbeState *state = user_data;
    (void)compressor;
    state->error = g_error_copy(error);
}

static void on_completed(AutoarCompressor *compressor, gpointer user_data) {
    ProbeState *state = user_data;
    (void)compressor;
    state->completed = TRUE;
}

static int check(gboolean condition, const char *message) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 0;
    }
    return 1;
}

int main(void) {
    static const char payload[] = "gnome-autoar HarmonyOS consumer test\n";
    ProbeState state = {0};
    GError *error = NULL;
    GFileInfo *archive_info = NULL;
    GList *sources = NULL;
    AutoarCompressor *compressor = NULL;
    GFile *input_file = NULL;
    GFile *output_directory = NULL;
    gchar *working_directory = NULL;
    gchar *input_path = NULL;
    gchar *output_path = NULL;
    gchar *combined_extension = NULL;
    int passed = 1;

    passed &= check(autoar_libarchive_quark() != 0,
                    "libarchive error domain must be registered");
    passed &= check(autoar_format_is_valid(AUTOAR_FORMAT_ZIP),
                    "ZIP must be a valid archive format");
    passed &= check(autoar_filter_is_valid(AUTOAR_FILTER_NONE),
                    "the no-filter mode must be valid");
    passed &= check(strcmp(autoar_format_get_extension(AUTOAR_FORMAT_ZIP),
                           "zip") == 0,
                    "ZIP extension must be zip");
    passed &= check(strcmp(autoar_format_get_mime_type(AUTOAR_FORMAT_ZIP),
                           "application/zip") == 0,
                    "ZIP MIME type must be application/zip");

    combined_extension = autoar_format_filter_get_extension(
        AUTOAR_FORMAT_ZIP, AUTOAR_FILTER_NONE);
    passed &= check(combined_extension != NULL &&
                        strcmp(combined_extension, ".zip") == 0,
                    "combined ZIP extension must be .zip");

    working_directory = g_get_current_dir();
    input_path = g_build_filename(working_directory, "autoar-input.txt", NULL);
    output_path = g_build_filename(working_directory, "autoar-output", NULL);
    if (g_mkdir_with_parents(output_path, 0700) != 0 ||
        !g_file_set_contents(input_path, payload, -1, &error)) {
        fprintf(stderr, "FAIL: could not prepare test files: %s\n",
                error ? error->message : "unknown error");
        passed = 0;
        goto cleanup;
    }

    input_file = g_file_new_for_path(input_path);
    output_directory = g_file_new_for_path(output_path);
    sources = g_list_append(sources, g_object_ref(input_file));
    compressor = autoar_compressor_new(sources, output_directory,
                                       AUTOAR_FORMAT_ZIP, AUTOAR_FILTER_NONE,
                                       FALSE);
    g_signal_connect(compressor, "decide-dest",
                     G_CALLBACK(on_decide_destination), &state);
    g_signal_connect(compressor, "error", G_CALLBACK(on_error), &state);
    g_signal_connect(compressor, "completed", G_CALLBACK(on_completed), &state);
    /* start() is synchronous; all callbacks run before it returns. */
    autoar_compressor_start(compressor, NULL);

    passed &= check(state.error == NULL, "ZIP creation must not report an error");
    passed &= check(state.completed, "ZIP creation must emit completed");
    passed &= check(state.destination != NULL,
                    "ZIP creation must select a destination");
    if (state.destination != NULL) {
        archive_info = g_file_query_info(
            state.destination,
            G_FILE_ATTRIBUTE_STANDARD_TYPE "," G_FILE_ATTRIBUTE_STANDARD_SIZE,
            G_FILE_QUERY_INFO_NONE, NULL, &error);
        passed &= check(archive_info != NULL &&
                            g_file_info_get_file_type(archive_info) ==
                                G_FILE_TYPE_REGULAR &&
                            g_file_info_get_size(archive_info) > 0,
                        "created ZIP must be a non-empty regular file");
    }

cleanup:
    if (error != NULL) {
        g_error_free(error);
    }
    if (state.error != NULL) {
        fprintf(stderr, "compressor error: %s\n", state.error->message);
        g_error_free(state.error);
    }
    if (archive_info != NULL) {
        g_object_unref(archive_info);
    }
    if (state.destination != NULL) {
        g_file_delete(state.destination, NULL, NULL);
        g_object_unref(state.destination);
    }
    if (compressor != NULL) {
        g_object_unref(compressor);
    }
    /* AutoarCompressor deep-copies and refs the source list. */
    g_list_free_full(sources, g_object_unref);
    if (input_file != NULL) {
        g_object_unref(input_file);
    }
    if (output_directory != NULL) {
        g_object_unref(output_directory);
    }
    g_remove(input_path);
    g_rmdir(output_path);
    g_free(combined_extension);
    g_free(output_path);
    g_free(input_path);
    g_free(working_directory);

    if (!passed) {
        return 1;
    }
    puts("gnome-autoar 0.5.2 consumer test: OK");
    return 0;
}

