#include <cursesw.h>

int construct_ncurses_window_for_link_test() {
    NCursesWindow window(static_cast<WINDOW *>(nullptr));
    return 0;
}

int (*volatile ncurses_cpp_link_probe)() =
    construct_ncurses_window_for_link_test;

int main() {
    return ncurses_cpp_link_probe == nullptr ? 1 : 0;
}
