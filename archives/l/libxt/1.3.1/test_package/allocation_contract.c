#include <X11/Intrinsic.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    char *block = XtMalloc(16);
    char *formatted = NULL;
    int *zeroed;
    int length;

    if (block == NULL)
        return 1;
    memset(block, 'A', 16);
    if (block[0] != 'A' || block[15] != 'A')
        return 2;

    zeroed = (int *) XtCalloc(4, sizeof(*zeroed));
    if (zeroed == NULL)
        return 3;
    if (zeroed[0] != 0 || zeroed[1] != 0 ||
        zeroed[2] != 0 || zeroed[3] != 0)
        return 4;
    XtFree((char *) zeroed);

    block = XtRealloc(block, 32);
    if (block == NULL)
        return 5;
    if (block[0] != 'A' || block[15] != 'A')
        return 6;

    block = XtReallocArray(block, 64, sizeof(*block));
    if (block == NULL)
        return 7;
    if (block[0] != 'A' || block[15] != 'A')
        return 8;
    XtFree(block);

    length = XtAsprintf(&formatted, "%s-%d", "libxt", 13);
    if (length != 8 || formatted == NULL)
        return 9;
    if (strcmp(formatted, "libxt-13") != 0)
        return 10;
    XtFree(formatted);

    puts("libXt allocation contract passed");
    return 0;
}
