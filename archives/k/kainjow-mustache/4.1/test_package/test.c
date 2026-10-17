#include <mustache.hpp>

#include <iostream>
#include <string>

int main() {
    using kainjow::mustache::data;
    using kainjow::mustache::mustache;

    mustache tmpl("Hello {{name}}! {{#enabled}}<{{value}}>{{/enabled}}");
    data context;
    context.set("name", "OpenHarmony");
    context.set("enabled", data::type::bool_true);
    context.set("value", "A&B");

    const std::string rendered = tmpl.render(context);
    const std::string expected = "Hello OpenHarmony! <A&amp;B>";
    if (!tmpl.is_valid() || rendered != expected) {
        std::cerr << "unexpected render result: " << rendered << '\n';
        return 1;
    }

    std::cout << rendered << '\n';
    return 0;
}
