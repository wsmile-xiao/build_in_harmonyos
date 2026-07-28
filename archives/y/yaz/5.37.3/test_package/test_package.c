#include <string.h>

#include <yaz/yaz-version.h>

int main(void) {
    char version[64] = {0};
    char revision[64] = {0};
    yaz_version(version, revision);
    return strcmp(version, "5.37.3") == 0 ? 0 : 1;
}
