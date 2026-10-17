#include <alsa/asoundlib.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int require_environment(const char *name, const char *expected)
{
    const char *actual = getenv(name);

    if (actual != NULL && strcmp(actual, expected) == 0)
        return 0;
    fprintf(stderr, "%s mismatch: expected=%s actual=%s\n",
            name, expected, actual == NULL ? "<unset>" : actual);
    return -1;
}

int main(int argc, char **argv)
{
    struct stat status;
    int update_result;

    if (argc != 5) {
        fputs("expected config-dir config-path plugin-dir tmp-dir\n", stderr);
        return 1;
    }
    if (require_environment("ALSA_CONFIG_DIR", argv[1]) < 0 ||
        require_environment("ALSA_CONFIG_PATH", argv[2]) < 0 ||
        require_environment("ALSA_PLUGIN_DIR", argv[3]) < 0 ||
        require_environment("TMPDIR", argv[4]) < 0)
        return 1;
    if (stat(argv[2], &status) < 0 || !S_ISREG(status.st_mode)) {
        fprintf(stderr, "ALSA_CONFIG_PATH is not a regular file: %s\n", argv[2]);
        return 1;
    }

    update_result = snd_config_update();
    if (update_result < 0) {
        fprintf(stderr, "snd_config_update failed: %d\n", update_result);
        return 1;
    }
    snd_config_update_free_global();
    puts("runtime metadata loaded the packaged ALSA configuration");
    return 0;
}
