#include <X11/Intrinsic.h>

#include <stdio.h>

int main(void)
{
    XtAppContext context;

    XtToolkitInitialize();
    context = XtCreateApplicationContext();
    if (context == NULL)
        return 1;
    if (XtAppGetExitFlag(context) != False)
        return 2;

    XtAppSetExitFlag(context);
    if (XtAppGetExitFlag(context) != True)
        return 3;

    XtDestroyApplicationContext(context);
    puts("libXt application-context contract passed");
    return 0;
}
