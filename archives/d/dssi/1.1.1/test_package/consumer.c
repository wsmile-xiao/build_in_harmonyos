#include <dssi.h>
#include <stdio.h>

int main(void)
{
    int controller = DSSI_CC(23) | DSSI_NRPN(1069);
    if (!DSSI_IS_CC(controller) || DSSI_CC_NUMBER(controller) != 23)
        return 1;
    if (!DSSI_IS_NRPN(controller) || DSSI_NRPN_NUMBER(controller) != 1069)
        return 2;
    puts("DSSI_CONSUMER_1_OF_1_PASS");
    return 0;
}
