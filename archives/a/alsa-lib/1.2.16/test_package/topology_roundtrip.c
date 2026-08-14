#include <stddef.h>

#include <alsa/topology.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void)
{
    static const unsigned char manifest_data[] = {0x41, 0x4c, 0x53, 0x41};
    snd_tplg_t *decoded = NULL;
    snd_tplg_t *reloaded = NULL;
    snd_tplg_t *source = NULL;
    char *saved = NULL;
    void *binary = NULL;
    size_t binary_size = 0;
    int result = 1;

    source = snd_tplg_new();
    if (source == NULL) {
        fputs("snd_tplg_new failed for source\n", stderr);
        goto done;
    }
    if (snd_tplg_set_manifest_data(
            source, manifest_data, (int)sizeof(manifest_data)
        ) < 0) {
        fputs("snd_tplg_set_manifest_data rejected the payload\n", stderr);
        goto done;
    }
    if (snd_tplg_build_bin(source, &binary, &binary_size) < 0 ||
        binary == NULL || binary_size == 0) {
        fputs("snd_tplg_build_bin did not produce a manifest binary\n", stderr);
        goto done;
    }

    decoded = snd_tplg_new();
    if (decoded == NULL) {
        fputs("snd_tplg_new failed for decoder\n", stderr);
        goto done;
    }
    if (snd_tplg_decode(decoded, binary, binary_size, 0) < 0) {
        fputs("snd_tplg_decode rejected the generated binary\n", stderr);
        goto done;
    }
    if (snd_tplg_save(decoded, &saved, SND_TPLG_SAVE_SORT) < 0 ||
        saved == NULL || strstr(saved, "SectionManifest") == NULL ||
        strstr(saved, "41:4c:53:41") == NULL) {
        fputs("snd_tplg_save did not reconstruct the manifest\n", stderr);
        goto done;
    }
    reloaded = snd_tplg_new();
    if (reloaded == NULL ||
        snd_tplg_load(reloaded, saved, strlen(saved)) < 0) {
        fputs("snd_tplg_load rejected the reconstructed manifest\n", stderr);
        goto done;
    }

    printf("topology manifest round-trip produced %zu bytes\n", binary_size);
    result = 0;

done:
    free(saved);
    free(binary);
    if (reloaded != NULL)
        snd_tplg_free(reloaded);
    if (decoded != NULL)
        snd_tplg_free(decoded);
    if (source != NULL)
        snd_tplg_free(source);
    return result;
}
