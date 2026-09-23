#include <dwg.h>
#include <dwg_api.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    Dwg_Data dwg;
    int err;
    memset(&dwg, 0, sizeof dwg);
    if (!is_dwg_entity("LINE") || is_dwg_entity("NOT_A_DWG_ENTITY")) {
        fprintf(stderr, "is_dwg_entity failed\n");
        return 1;
    }
    err = dwg_read_file("no-such-file.dwg", &dwg);
    if (err == 0) {
        fprintf(stderr, "expected missing-file error\n");
        return 1;
    }
    printf("libredwg version=%d entity=LINE read_missing=%d\n", LIBREDWG_VERSION, err);
    return 0;
}
