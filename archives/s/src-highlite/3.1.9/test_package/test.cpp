// Consumer test for src-highlite: links the srchilite library as a library
// user would, drives the public SourceHighlight API end to end (real C++
// source -> highlighted HTML document) and asserts on the produced content.
#include <srchilite/sourcehighlight.h>

#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char **argv) {
    if (argc < 2) {
        std::cerr << "usage: consumer_test <source-highlight data dir>\n";
        return 2;
    }
    const std::string data_dir = argv[1];

    // 1. Real API call: highlight a small C++ snippet into an HTML file.
    const std::string in_path = "consumer_test_input.cpp";
    const std::string out_path = "consumer_test_output.html";
    {
        std::ofstream in(in_path.c_str());
        in << "// a comment\nint main() { return 42; }\n";
    }
    try {
        srchilite::SourceHighlight hl("html.outlang");
        hl.setDataDir(data_dir);
        hl.highlight(in_path, out_path, "cpp.lang");
    } catch (const std::exception &e) {
        std::cerr << "highlight() failed: " << e.what() << "\n";
        return 2;
    }

    // 2. Assert on the produced document (verifiable behaviour, not a print).
    std::ifstream out(out_path.c_str());
    if (!out) {
        std::cerr << "no output produced\n";
        return 1;
    }
    std::stringstream buffer;
    buffer << out.rdbuf();
    const std::string html = buffer.str();
    const bool ok = html.find("main") != std::string::npos
                 && html.find("comment") != std::string::npos
                 && html.find("<font") != std::string::npos
                 && html.find("<pre>") != std::string::npos;
    if (!ok) {
        std::cerr << "output lacks expected highlighted markup\n";
        return 1;
    }
    std::cout << "consumer_test: highlighted " << html.size()
              << " bytes OK\n";
    return 0;
}
