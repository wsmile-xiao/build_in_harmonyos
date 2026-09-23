// test_package/test_wave.cpp — boost1.84-wave 1.84.0 L1 smoke test.
// Exercises Boost.Wave (context + lexer iteration + conditional evaluation),
// Boost.Filesystem (path used by wave), and Boost.Thread (tss symbols pulled
// in through the wave context pool).
#include <boost/wave.hpp>
#include <boost/wave/cpplexer/cpp_lex_token.hpp>
#include <boost/wave/cpplexer/cpp_lex_iterator.hpp>
#include <boost/filesystem/path.hpp>
#include <iostream>
#include <string>

int main() {
    // 1. Wave: preprocess a small input with conditionals and macros
    std::string input(
        "#define GREETING wave\n"
        "#if 1\n"
        "hello_\n"
        "#else\n"
        "never_printed\n"
        "#endif\n"
        "GREETING\n"
    );

    try {
        typedef boost::wave::cpplexer::lex_token<> token_type;
        typedef boost::wave::cpplexer::lex_iterator<token_type> lex_iterator_type;
        typedef boost::wave::context<std::string::iterator, lex_iterator_type> context_type;

        context_type ctx(input.begin(), input.end(), "test_wave.cpp");

        std::string result;
        for (context_type::iterator_type first = ctx.begin(), last = ctx.end();
             first != last; ++first) {
            result += first->get_value().c_str();
        }

        // The preprocessed output must contain the kept branch and the
        // expanded macro, but not the dropped branch.
        if (result.find("hello_") == std::string::npos) {
            std::cerr << "wave: kept branch missing in output: " << result << std::endl;
            return 1;
        }
        if (result.find("wave") == std::string::npos) {
            std::cerr << "wave: macro not expanded in output: " << result << std::endl;
            return 1;
        }
        if (result.find("never_printed") != std::string::npos) {
            std::cerr << "wave: dropped branch leaked into output: " << result << std::endl;
            return 1;
        }
        std::cout << "wave: preprocessed output ok" << std::endl;
    } catch (boost::wave::cpp_exception const &x) {
        std::cerr << "wave: preprocessing failed: " << x.file_name()
                  << "(" << x.line_no() << "): " << x.description() << std::endl;
        return 1;
    } catch (std::exception const &x) {
        std::cerr << "Exception: " << x.what() << std::endl;
        return 2;
    }

    // 2. Wave: macro expansion count sanity (token iteration exercised)
    {
        std::string input2("#define A 1\n#define B A+A\nB\n");
        typedef boost::wave::cpplexer::lex_token<> token_type;
        typedef boost::wave::cpplexer::lex_iterator<token_type> lex_iterator_type;
        typedef boost::wave::context<std::string::iterator, lex_iterator_type> context_type;
        context_type ctx(input2.begin(), input2.end(), "test_wave2.cpp");
        int tokens = 0;
        for (context_type::iterator_type first = ctx.begin(), last = ctx.end();
             first != last; ++first) {
            ++tokens;
        }
        // "1 + 1 \n" -> at least 3 non-whitespace tokens
        if (tokens < 3) {
            std::cerr << "wave: unexpected token count " << tokens << std::endl;
            return 1;
        }
        std::cout << "wave: token iteration ok (" << tokens << " tokens)" << std::endl;
    }

    // 3. Filesystem: wave's path machinery
    boost::filesystem::path p("some/include/dir");
    if (p.filename().string() != "dir") {
        std::cerr << "filesystem: unexpected filename " << p.filename() << std::endl;
        return 1;
    }
    std::cout << "filesystem: path ok" << std::endl;

    return 0;
}
