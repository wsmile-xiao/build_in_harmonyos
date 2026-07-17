#include <X11/Xlib.h>
#include <iostream>

int main() {
    // 仅做编译测试，不实际连接 X Server
    std::cout << "X11 headers present, test passed!" << std::endl;
    return 0;
}
