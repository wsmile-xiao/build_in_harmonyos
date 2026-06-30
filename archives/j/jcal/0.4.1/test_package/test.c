#include <stdio.h>
#include <stdlib.h>
#include <jalali/jalali.h>
#include <jalali/jtime.h>

int main(void) {
    struct jtm j;
    time_t t = 0;
    jlocaltime_r(&t, &j);
    printf("test jcal 0.4.1: jlocaltime_r OK, year=%d\n", j.tm_year);
    return 0;
}
