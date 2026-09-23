#include <slp.h>
#include <string.h>

int main(void)
{
    SLPSrvURL *u = 0;
    if (SLPParseSrvURL("service:demo://[::1]:9/p", &u) != SLP_OK) {
        return 1;
    }
    if (u == 0) return 2;
    if (u->s_pcNetFamily == 0 || strcmp(u->s_pcNetFamily, "v6") != 0) return 3;
    if (u->s_pcHost == 0 || strcmp(u->s_pcHost, "::1") != 0) return 4;
    if (u->s_iPort != 9) return 5;
    SLPFree(u);
    return 0;
}
