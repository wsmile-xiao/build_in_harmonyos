/* libcifpp 10.0.4 test_package consumer probe.
 * Creates a cif::file via the public API — verifies libcifpp links
 * and the header is usable. No CIF data required.
 */
#include <cif++/cif++.hpp>
#include <iostream>

int main(void)
{
    cif::file f;
    /* Reaching here proves libcifpp linked + initialized. */
    std::cout << "libcifpp OK" << std::endl;
    return 0;
}
