#include <minja/minja.hpp>
#include <minja/chat-template.hpp>
#include <iostream>
#include <string>

int main() {
    using nlohmann::ordered_json;
    auto ast = minja::Parser::parse("Hello {{ name }}!", {});
    auto context = minja::Context::make(minja::Value(ordered_json{{"name", "HarmonyOS"}}));
    const std::string rendered = ast->render(context);
    if (rendered != "Hello HarmonyOS!") {
        std::cerr << "minja render mismatch: " << rendered << '\n';
        return 1;
    }

    minja::chat_template chat(
        "{% for message in messages %}{{ '<|' + message.role + '|>' + message.content }}"
        "{% endfor %}{{ '<|assistant|>' if add_generation_prompt else '' }}", "", "");
    const auto messages = ordered_json::parse(R"([{"role":"user","content":"hello"}])");
    const std::string chat_result = chat.apply(messages, ordered_json::array(), true, {});
    if (chat_result != "<|user|>hello<|assistant|>") {
        std::cerr << "chat-template mismatch: " << chat_result << '\n';
        return 2;
    }

    std::cout << "minja header and nlohmann_json consumer checks passed\\n";
    return 0;
}
