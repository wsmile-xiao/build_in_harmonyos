// Consumer test for sexpp 0.9.1 — uses only the public API exposed by the
// installed headers: parse an S-expression from a stream and print it back
// in canonical form, verifying a round-trip through the public interface.
#include <iostream>
#include <sstream>
#include <string>

#include <sexpp/sexp.h>

int main() {
    // Public API: sexp_input_stream_t reads from a std::istream.
    // (Numeric tokens must be passed as quoted strings per upstream grammar.)
    std::istringstream input("(hello (world \"42\"))");
    sexp::sexp_input_stream_t is(&input);

    // Scan one S-expression object through the public scanner.
    auto obj = is.set_byte_size(8)->get_char()->scan_object();
    if (!obj) {
        std::cerr << "FAIL: scan_object returned null" << std::endl;
        return 1;
    }

    // Print it back through the public output stream (canonical format).
    std::ostringstream out;
    sexp::sexp_output_stream_t os(&out);
    os.print_canonical(obj);

    std::string printed = out.str();
    std::cout << "canonical: " << printed << std::endl;

    // Verify the round-trip produced the expected canonical output.
    // Canonical output for a list: length-prefixed string form.
    if (printed.find("hello") == std::string::npos ||
        printed.find("world") == std::string::npos ||
        printed.find("42") == std::string::npos) {
        std::cerr << "FAIL: unexpected canonical output: " << printed << std::endl;
        return 1;
    }
    return 0;
}
