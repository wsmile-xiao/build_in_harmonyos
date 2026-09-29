/*
 * HarmonyOS-specific probe.
 *
 * On OHOS, libvosk.so is consumed at runtime through the platform dynamic
 * loader (musl ldso) — the Python (`ctypes`), Java and C# bindings all
 * dlopen() the shared library instead of linking it at build time. This probe
 * reproduces exactly that path: it does NOT link libvosk.so, it loads it from
 * an absolute path and resolves the public C API symbols with dlsym().
 *
 * usage: ohos_dlopen_probe <path/to/libvosk.so>
 */
#include <dlfcn.h>
#include <stdio.h>

static const char *const PUBLIC_SYMBOLS[] = {
    "vosk_model_new",
    "vosk_model_free",
    "vosk_spk_model_new",
    "vosk_recognizer_new",
    "vosk_recognizer_accept_waveform",
    "vosk_recognizer_result",
    "vosk_recognizer_final_result",
    "vosk_text_processor_new",
    "vosk_text_processor_itn",
    "vosk_set_log_level",
    NULL
};

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <path/to/libvosk.so>\n", argv[0]);
        return 2;
    }

    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (handle == NULL) {
        printf("FAIL: dlopen('%s'): %s\n", argv[1], dlerror());
        return 1;
    }
    printf("PASS: dlopen('%s')\n", argv[1]);

    int resolved = 0;
    int missing = 0;
    for (int i = 0; PUBLIC_SYMBOLS[i] != NULL; ++i) {
        void *sym = dlsym(handle, PUBLIC_SYMBOLS[i]);
        if (sym != NULL) {
            printf("  resolved %s -> %p\n", PUBLIC_SYMBOLS[i], sym);
            resolved++;
        } else {
            printf("  MISSING  %s\n", PUBLIC_SYMBOLS[i]);
            missing++;
        }
    }

    dlclose(handle);

    if (missing != 0) {
        printf("FAIL: %d/%d public symbols unresolved\n", missing,
               resolved + missing);
        return 1;
    }
    printf("PASS: all %d public C API symbols resolved\n", resolved);
    return 0;
}
