#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if !defined(__OHOS__)
#error "This test must be compiled for HarmonyOS"
#endif

static int write_file(const char *path)
{
    FILE *file = fopen(path, "wb");
    if (!file) {
        fprintf(stderr, "FAIL: cannot write HarmonyOS temp file %s: %s\n",
                path, strerror(errno));
        return 0;
    }
    fputs("<?xml version=\"1.0\"?><plist version=\"1.0\"><dict>"
          "<key>platform</key><string>HarmonyOS</string></dict></plist>", file);
    return fclose(file) == 0;
}

static int contains(const char *path, const char *needle)
{
    char buffer[4096];
    size_t length;
    FILE *file = fopen(path, "rb");
    if (!file) {
        fprintf(stderr, "FAIL: cannot read HarmonyOS output %s: %s\n",
                path, strerror(errno));
        return 0;
    }
    length = fread(buffer, 1, sizeof(buffer) - 1, file);
    fclose(file);
    buffer[length] = '\0';
    return strstr(buffer, needle) != NULL;
}

static int run_tool(const char *command)
{
    int status = system(command);
    if (status != 0) {
        fprintf(stderr, "FAIL: HarmonyOS command returned status %d: %s\n",
                status, command);
        return 0;
    }
    return 1;
}

int main(void)
{
    const char *tmpdir = getenv("TMPDIR");
    char input[512];
    char output[512];
    char command[2048];

    if (!tmpdir || !tmpdir[0]) {
        tmpdir = "/data/local/tmp";
    }
    if (snprintf(input, sizeof(input), "%s/libplist-util-ohos-input.plist", tmpdir)
        >= (int)sizeof(input)
        || snprintf(output, sizeof(output), "%s/libplist-util-ohos-output.json", tmpdir)
           >= (int)sizeof(output)) {
        fprintf(stderr, "FAIL: HarmonyOS temporary path is too long\n");
        return 1;
    }
    if (!write_file(input)) {
        return 1;
    }

    snprintf(command, sizeof(command),
             "plistutil -i '%s' -o '%s' -f json", input, output);
    if (!run_tool(command) || !contains(output, "HarmonyOS")) {
        fprintf(stderr, "FAIL: plistutil did not round-trip data in HarmonyOS temp storage\n");
        remove(input);
        remove(output);
        return 1;
    }

    remove(input);
    remove(output);
    printf("PASS: HarmonyOS plistutil temp-file conversion test\n");
    return 0;
}
