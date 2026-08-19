// test_package/test.cpp — L1 consumer test for argh 1.3.2
// Verifies argh's header-only API by parsing command-line arguments
// and asserting the parsing results (at least 3 assertion groups).

#include <argh.h>
#include <cassert>
#include <string>

int main() {
    // ---- Test 1: Flag parsing ----
    {
        const char* argv[] = {"prog", "--verbose", "--flag"};
        argh::parser parser(3, argv);
        assert(parser["--verbose"] == true);   // flag present
        assert(parser["--flag"] == true);      // flag present
        assert(parser["--missing"] == false);  // flag absent
    }

    // ---- Test 2: Parameter parsing ----
    {
        const char* argv[] = {"prog", "--output", "file.txt", "--count", "42"};
        argh::parser parser(5, argv);
        assert(parser("--output").str() == "file.txt");  // param value
        assert(parser("--count").str() == "42");         // param value
        assert(parser("--output") == "file.txt");  // param value
        assert(parser("--count") == "42");         // param value
        assert(parser("--missing") == "");          // missing param → empty
    }

    // ---- Test 3: Positional arguments ----
    {
        const char* argv[] = {"prog", "input.dat", "output.dat"};
        argh::parser parser(3, argv);
        assert(parser[0] == "input.dat");    // first positional
        assert(parser[1] == "output.dat");    // second positional
        assert(parser.size() == 2);          // positional count
    }

    // ---- Test 4: Mixed flags, params and positionals ----
    {
        const char* argv[] = {"prog", "pos1", "--flag", "pos2", "--opt=val"};
        argh::parser parser(5, argv);
        assert(parser["--flag"] == true);     // flag detected
        assert(parser("--opt") == "val"); // param with = sign
        assert(parser[0] == "pos1");          // first positional
        assert(parser[1] == "pos2");           // second positional
    }

    return 0;
}
