#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int write_file(const char *path, const char *contents)
{
    FILE *file = fopen(path, "wb");
    if (!file) {
        fprintf(stderr, "FAIL: cannot write %s: %s\n", path, strerror(errno));
        return 0;
    }
    if (fputs(contents, file) == EOF || fclose(file) != 0) {
        fprintf(stderr, "FAIL: cannot finish writing %s\n", path);
        return 0;
    }
    return 1;
}

static int contains(const char *path, const char *needle)
{
    char buffer[4096];
    size_t length;
    FILE *file = fopen(path, "rb");
    if (!file) {
        fprintf(stderr, "FAIL: cannot read %s: %s\n", path, strerror(errno));
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
        fprintf(stderr, "FAIL: command returned status %d: %s\n", status, command);
        return 0;
    }
    return 1;
}

int main(void)
{
    const char *tmpdir = getenv("TMPDIR");
    char input[512];
    char json[512];
    char xml[512];
    char version[512];
    char command[2048];
    const char *plist =
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" "
        "\"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n"
        "<plist version=\"1.0\"><dict><key>name</key>"
        "<string>libplist-util</string></dict></plist>\n";

    if (!tmpdir || !tmpdir[0]) {
        tmpdir = ".";
    }
    if (snprintf(input, sizeof(input), "%s/libplist-util-input.plist", tmpdir)
        >= (int)sizeof(input)
        || snprintf(json, sizeof(json), "%s/libplist-util-output.json", tmpdir)
           >= (int)sizeof(json)
        || snprintf(xml, sizeof(xml), "%s/libplist-util-roundtrip.plist", tmpdir)
           >= (int)sizeof(xml)
        || snprintf(version, sizeof(version), "%s/libplist-util-version.txt", tmpdir)
           >= (int)sizeof(version)) {
        fprintf(stderr, "FAIL: temporary path is too long\n");
        return 1;
    }

    if (!write_file(input, plist)) {
        return 1;
    }
    snprintf(command, sizeof(command), "plistutil --version > '%s' 2>&1", version);
    if (!run_tool(command) || !contains(version, "plistutil 2.7.0")) {
        fprintf(stderr, "FAIL: packaged plistutil did not report version 2.7.0\n");
        remove(input);
        remove(version);
        return 1;
    }
    snprintf(command, sizeof(command),
             "plistutil -i '%s' -o '%s' -f json", input, json);
    if (!run_tool(command) || !contains(json, "libplist-util")) {
        fprintf(stderr, "FAIL: XML to JSON conversion did not preserve the value\n");
        remove(input);
        remove(json);
        remove(version);
        return 1;
    }
    snprintf(command, sizeof(command),
             "plistutil -i '%s' -o '%s' -f xml", json, xml);
    if (!run_tool(command) || !contains(xml, "<key>name</key>")) {
        fprintf(stderr, "FAIL: JSON to XML conversion did not preserve the key\n");
        remove(input);
        remove(json);
        remove(xml);
        remove(version);
        return 1;
    }

    remove(input);
    remove(json);
    remove(xml);
    remove(version);
    printf("PASS: plistutil version and XML/JSON round-trip test\n");
    return 0;
}
