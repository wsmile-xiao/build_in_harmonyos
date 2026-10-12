#include <TooN/TooN.h>

int main() {
    TooN::Vector<3> value;
    value[0] = 1.0;
    value[1] = 2.0;
    value[2] = 3.0;
    return value[0] == 1.0 && value[1] == 2.0 && value[2] == 3.0 ? 0 : 1;
}
