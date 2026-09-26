#include <squirrel.h>

int main() {
    HSQUIRRELVM vm = sq_open(1024);
    if (vm == nullptr) {
        return 1;
    }
    sq_pushroottable(vm);
    sq_pop(vm, 1);
    sq_close(vm);
    return 0;
}
