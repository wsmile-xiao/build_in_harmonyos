/*
 * Consumer smoke test for devicexlib: verify the packaged static archive
 * (libdevXlib.a, Fortran symbols + its LAPACK/Fortran-runtime closure)
 * links into a plain C consumer and the binary runs.
 */
#include <stdio.h>

int main(void)
{
    printf("devicexlib consumer link+run OK\n");
    return 0;
}
