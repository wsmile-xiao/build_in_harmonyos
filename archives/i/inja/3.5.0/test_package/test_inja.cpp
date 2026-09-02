#include <inja/inja.hpp>

#include <iostream>
#include <string>

int main() {
    inja::json data = {
        {"name", "HarmonyOS"},
        {"items", {"C++", "Conan", "Inja"}},
    };

    const std::string greeting = inja::render("Hello {{ name }}!", data);
    if (greeting != "Hello HarmonyOS!") {
        std::cerr << "FAIL: render result was '" << greeting << "'\n";
        return 1;
    }

    inja::Environment environment;
    const std::string list = environment.render(
        "{% for item in items %}{{ loop.index1 }}:{{ item }};{% endfor %}",
        data);
    if (list != "1:C++;2:Conan;3:Inja;") {
        std::cerr << "FAIL: loop result was '" << list << "'\n";
        return 2;
    }

    bool render_error_seen = false;
    try {
        environment.render("{{ missing }}", data);
    } catch (const inja::RenderError&) {
        render_error_seen = true;
    }
    if (!render_error_seen) {
        std::cerr << "FAIL: missing variable did not raise RenderError\n";
        return 3;
    }

    const std::string conditional = environment.render(
        "{% if items %}non-empty{% else %}empty{% endif %}", data);
    if (conditional != "non-empty") {
        std::cerr << "FAIL: conditional result was '" << conditional << "'\n";
        return 4;
    }

    std::cout << "PASS: inja render, Environment, loop, conditional, and error API checks\n";
    return 0;
}
