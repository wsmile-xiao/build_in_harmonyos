#include <slp.h>

int main(void)
{
    SLPSrvURL *u = 0;
    SLPError rc = SLPParseSrvURL("this is not a service url", &u);
    if (rc == SLP_OK) {
        return 1;
    }
    return 0;
}
