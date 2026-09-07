#include <slp.h>
#include <string.h>

int main(void)
{
    SLPSrvURL *u = 0;
    if (SLPParseSrvURL("service:demo://myhost:427/path", &u) != SLP_OK) {
        return 1;
    }
    if (u == 0) return 2;
    if (u->s_pcSrvType == 0 || strcmp(u->s_pcSrvType, "service:demo") != 0) return 3;
    if (u->s_pcHost == 0 || strcmp(u->s_pcHost, "myhost") != 0) return 4;
    if (u->s_iPort != 427) return 5;
    if (u->s_pcNetFamily == 0 || strcmp(u->s_pcNetFamily, "") != 0) return 6;
    if (u->s_pcSrvPart == 0 || strcmp(u->s_pcSrvPart, "path") != 0) return 7;
    SLPFree(u);
    return 0;
}
