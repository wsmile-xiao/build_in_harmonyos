#include <slp.h>
#include <string.h>

int main(void)
{
    const char *in = "a b=1!()";
    char *esc = 0;
    char *back = 0;

    if (SLPEscape(in, &esc, SLP_FALSE) != SLP_OK) return 1;
    if (esc == 0 || strcmp(esc, in) == 0) return 2;
    if (SLPUnescape(esc, &back, SLP_FALSE) != SLP_OK) return 3;
    if (back == 0 || strcmp(back, in) != 0) return 4;
    SLPFree(back);
    SLPFree(esc);
    return 0;
}
