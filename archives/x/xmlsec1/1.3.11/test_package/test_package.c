#include <xmlsec/xmlsec.h>

int main(void) {
    if (xmlSecInit() < 0) {
        return 1;
    }
    xmlSecShutdown();
    return 0;
}
