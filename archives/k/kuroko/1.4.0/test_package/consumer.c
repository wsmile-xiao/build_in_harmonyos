#include <kuroko/kuroko.h>
#include <kuroko/vm.h>

int main(void) {
    krk_initVM(0);
    krk_startModule("__main__");
    krk_interpret("import kuroko\nprint('Kuroko', kuroko.version)\n", "<consumer>");
    krk_freeVM();
    return 0;
}
