#ifndef API_HEADER
#error "API_HEADER must name one installed ALSA header"
#endif

#ifndef API_SYMBOL
#error "API_SYMBOL must name one public ALSA function"
#endif

#include <alsa/asoundlib.h>
#include API_HEADER

int main(void)
{
    __typeof__(&API_SYMBOL) volatile symbol = &API_SYMBOL;
    return symbol == 0;
}
