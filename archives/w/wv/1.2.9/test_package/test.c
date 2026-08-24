#include <stdio.h>

#include <wv/wv.h>

int main(void) {
    DTTM dttm;
    SHD shading;
    DCS dcs;

    wvInitDTTM(&dttm);
    wvInitSHD(&shading);
    wvInitDCS(&dcs);

    if (dttm.mint != 0 || dttm.hr != 0 || dttm.dom != 0 ||
        dttm.mon != 0 || dttm.yr != 0 || dttm.wdy != 0 ||
        shading.icoFore != 0 || shading.icoBack != 0 || shading.ipat != 0 ||
        dcs.fdct != 0 || dcs.count != 0 || dcs.reserved != 0) {
        fprintf(stderr, "wv initializers did not clear their structures\n");
        return 1;
    }

    puts("wv API assertions: 3 passed");
    return 0;
}
