#include <core/property.h>
#include <core/signal.h>
#include <iostream>

// Test properties-cpp header-only library
int main() {
    // Create a simple property
    core::Property<int> prop(42);
    
    std::cout << "Initial value: " << prop.get() << std::endl;
    
    // Set new value
    prop.set(100);
    
    std::cout << "New value: " << prop.get() << std::endl;
    
    // Test signal connection
    core::Signal<int> signal;
    bool signal_received = false;
    
    auto connection = signal.connect([&](int value) {
        std::cout << "Signal received with value: " << value << std::endl;
        signal_received = true;
    });
    
    signal(123);
    
    if (signal_received) {
        std::cout << "properties-cpp test PASSED" << std::endl;
        return 0;
    } else {
        std::cerr << "properties-cpp test FAILED" << std::endl;
        return 1;
    }
}
