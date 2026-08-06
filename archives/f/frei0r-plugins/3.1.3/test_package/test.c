#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <frei0r.h>

int main(void) {
    /* Verify frei0r API version is defined (R34: test depends on the package) */
    if (FREI0R_MAJOR_VERSION != 1) {
        fprintf(stderr, "FREI0R_MAJOR_VERSION mismatch: expected 1, got %d\n",
                FREI0R_MAJOR_VERSION);
        return 1;
    }
    printf("frei0r API major version: %d\n", FREI0R_MAJOR_VERSION);

    /* Scan for installed plugin .so files to verify package contents */
    const char *plugin_dir = getenv("FREI0R_PLUGIN_DIR");
    if (plugin_dir) {
        DIR *dir = opendir(plugin_dir);
        if (dir) {
            int count = 0;
            struct dirent *entry;
            while ((entry = readdir(dir)) != NULL) {
                if (strstr(entry->d_name, ".so") != NULL) {
                    count++;
                }
            }
            closedir(dir);
            printf("Found %d plugin .so files in %s\n", count, plugin_dir);
            if (count == 0) {
                fprintf(stderr, "ERROR: No plugins found in %s\n", plugin_dir);
                return 1;
            }
        } else {
            fprintf(stderr, "ERROR: Cannot open plugin dir %s\n", plugin_dir);
            return 1;
        }
    } else {
        printf("FREI0R_PLUGIN_DIR not set, skipping plugin scan\n");
    }

    printf("test frei0r-plugins 3.1.3: OK\n");
    return 0;
}
