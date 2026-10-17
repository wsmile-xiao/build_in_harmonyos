#include <slp.h>

int main(void)
{
    SLPSrvURL *u = 0;
    if (SLPParseSrvURL("service:demo://myhost/srv", &u) != SLP_OK) {
        return 1;
    }
    if (u == 0) return 2;
    if (u->s_iPort != 0) return 3;
    if (u->s_pcHost == 0 || strcmp(u->s_pcHost, "myhost") != 0) return 4;
    SLPFree(u);
    return 0;
}
