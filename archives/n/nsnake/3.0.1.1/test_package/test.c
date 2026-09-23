#include <stdlib.h>

int main(void) {
    return system("nsnake --version") == 0 ? 0 : 1;
}
