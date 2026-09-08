#include "timbl/TimblAPI.h"
#include <iostream>

int main() {
    // Test that we can create a TimblAPI experiment object
    // This is the core API of the timbl library
    Timbl::TimblAPI *exp = new Timbl::TimblAPI("-a IGTREE +vDI+DB+F", "test_timbl");
    if (exp) {
        std::cout << "timbl 6.1: TimblAPI object created successfully" << std::endl;
        delete exp;
        return 0;
    } else {
        std::cerr << "timbl 6.1: Failed to create TimblAPI object" << std::endl;
        return 1;
    }
}
