#include <glibmm/ustring.h>

#include <cstdlib>

int main() {
    Glib::ustring value = "OpenHarmony";
    if (value.bytes() != 11) {
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
