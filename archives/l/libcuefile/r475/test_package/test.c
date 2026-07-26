#include <stdio.h>
#include <cuetools/cd.h>

int main(void)
{
    Cd *cd = cd_init();
    Track *track;

    if (cd == NULL) {
        if (fputs("cd_init failed\n", stderr) == EOF) {
            return 4;
        }
        return 1;
    }
    cd_set_mode(cd, MODE_CD_DA);
    if (cd_get_mode(cd) != MODE_CD_DA) {
        cd_delete(cd);
        return 2;
    }
    track = cd_add_track(cd);
    if (track == NULL || cd_get_ntrack(cd) != 1) {
        cd_delete(cd);
        return 3;
    }

    cd_delete(cd);
    if (puts("libcuefile API test: OK") == EOF) {
        return 4;
    }
    return 0;
}
