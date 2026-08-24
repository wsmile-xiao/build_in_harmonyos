#include <api/BamAlignment.h>

#include <iostream>

int main()
{
    BamTools::BamAlignment alignment;

    alignment.SetIsMapped(false);
    if (alignment.IsMapped()) {
        std::cerr << "SetIsMapped(false) did not clear the initial flag\n";
        return 1;
    }

    alignment.SetIsMapped(true);
    if (!alignment.IsMapped()) {
        std::cerr << "SetIsMapped(true) did not update the flag\n";
        return 2;
    }

    alignment.SetIsMapped(false);
    if (alignment.IsMapped()) {
        std::cerr << "SetIsMapped(false) did not clear the flag\n";
        return 3;
    }

    std::cout << "BamTools alignment flag API verified\n";
    return 0;
}
