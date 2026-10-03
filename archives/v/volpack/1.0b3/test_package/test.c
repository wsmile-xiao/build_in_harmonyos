#include <volpack.h>
#include <stdio.h>

int main(void)
{
    vpContext *context = vpCreateContext();
    int x = 0, y = 0, z = 0;
    if (context == NULL)
        return 1;
    if (vpSetVolumeSize(context, 2, 3, 4) != VP_OK)
        return 2;
    if (vpGeti(context, VP_XLEN, &x) != VP_OK || x != 2)
        return 3;
    if (vpGeti(context, VP_YLEN, &y) != VP_OK || y != 3)
        return 4;
    if (vpGeti(context, VP_ZLEN, &z) != VP_OK || z != 4)
        return 5;
    vpDestroyContext(context);
    puts("VolPack consumer API: PASS");
    return 0;
}
