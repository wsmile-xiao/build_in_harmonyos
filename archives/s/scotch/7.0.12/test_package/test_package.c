#include <stdio.h>
#include <scotch.h>

int main(void) {
    int major = 0;
    int release = 0;
    int patch = 0;
    SCOTCH_version(&major, &release, &patch);
    return major == 7 && release == 0 && patch == 12 ? 0 : 1;
}
