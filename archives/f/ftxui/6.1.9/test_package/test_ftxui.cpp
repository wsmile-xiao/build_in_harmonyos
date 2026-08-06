// test_ftxui.cpp — Consumer test for ftxui 6.1.9
// Verifies that the ftxui library can be linked and its API works correctly.
#include <ftxui/dom/elements.hpp>
#include <ftxui/screen/screen.hpp>
#include <string>
#include <iostream>

int main() {
    using namespace ftxui;

    // Create a simple text element
    Element element = text("Hello, FTXUI!");

    // Render to a fixed-size screen
    auto screen = Screen::Create(Dimension::Fixed(20), Dimension::Fixed(1));
    Render(screen, element);

    // Verify the rendered output contains expected text
    std::string output = screen.ToString();
    if (output.find("Hello, FTXUI!") != std::string::npos) {
        std::cout << "ftxui test: PASSED" << std::endl;
        return 0;
    }
    std::cerr << "ftxui test: FAILED - expected 'Hello, FTXUI!' in output" << std::endl;
    return 1;
}
