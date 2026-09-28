#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

void test1();
void test2();
void test3();
void test4();
void test5();
void test6();
void test7();
void test8();
void test9();
void test10();
void test11();
void test12();
void test13();
void test14();
void test15();
void test16();
void test17();
void test18();
void test19();
void test20();
void test21();
void test22();
void test23();
void test24();
void test25();
void test26();
void test27();
void test28();
void test29();
void test30();
void test31();
void test32();
void test33();

namespace {

bool copy_file(const char *source, const char *destination)
{
    std::ifstream input(source, std::ios::binary);
    std::ofstream output(destination, std::ios::binary);
    output << input.rdbuf();
    return input.good() || input.eof() ? output.good() : false;
}

bool prepare_midi_fixture(const char *destination)
{
    test4();
    return copy_file("test4.mid", destination);
}

} // namespace

int main(int argc, char **argv)
{
    if (argc != 2) {
        std::cerr << "usage: portsmf_upstream_tests <1..33>\n";
        return 2;
    }
    const int test_number = std::atoi(argv[1]);
    if (test_number < 1 || test_number > 33) {
        std::cerr << "invalid upstream test number\n";
        return 2;
    }

    if (test_number == 32 && !prepare_midi_fixture("jsb-wtc-c-f.mid")) {
        std::cerr << "could not prepare MIDI fixture for test32\n";
        return 1;
    }
    if (test_number == 33 && !prepare_midi_fixture("be-ps-05.mid")) {
        std::cerr << "could not prepare MIDI fixture for test33\n";
        return 1;
    }

    void (*tests[])() = {
        test1, test2, test3, test4, test5, test6, test7, test8, test9,
        test10, test11, test12, test13, test14, test15, test16, test17,
        test18, test19, test20, test21, test22, test23, test24, test25,
        test26, test27, test28, test29, test30, test31, test32, test33,
    };
    tests[test_number - 1]();
    std::cout << "upstream test " << test_number << " passed\n";
    return 0;
}
