/* Verify that the test preload is active and implements a working tmpfile. */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    int (*active)(void) = (int (*)(void))dlsym(RTLD_DEFAULT, "binutils_tmpfile_shim_active");
    const char value[] = "binutils runtime probe";
    char actual[sizeof(value)];
    FILE *stream;

    if (active == NULL || active() != 1) {
        fputs("[FAIL] tmpfile preload marker missing\n", stderr);
        return 1;
    }
    stream = tmpfile();
    if (stream == NULL) {
        perror("[FAIL] tmpfile");
        return 2;
    }
    if (fwrite(value, 1, sizeof(value), stream) != sizeof(value)
        || fflush(stream) != 0 || fseek(stream, 0, SEEK_SET) != 0
        || fread(actual, 1, sizeof(actual), stream) != sizeof(actual)
        || memcmp(actual, value, sizeof(value)) != 0) {
        fputs("[FAIL] tmpfile round trip\n", stderr);
        fclose(stream);
        return 3;
    }
    if (fclose(stream) != 0) {
        perror("[FAIL] fclose");
        return 4;
    }
    puts("[PASS] tmpfile preload active; write/read/seek/close verified");
    return 0;
}
