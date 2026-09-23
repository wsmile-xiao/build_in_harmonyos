#include <slp.h>

int main(void)
{
    SLPHandle h = 0;
    if (SLPOpen("en", SLP_FALSE, &h) != SLP_OK) {
        return 1;
    }
    if (h == 0) {
        return 2;
    }
    SLPClose(h);
    return 0;
}
