// test_package — yomm2 消费者验证
// 真实链接 libyomm2 并执行开放多方法分派（blackbox 风格的独立断言用例）。
#include <iostream>
#include <string>

#include <yorel/yomm2/cute.hpp>

using yorel::yomm2::virtual_;

struct Animal {
    virtual ~Animal() {}
};

struct Dog : Animal {};
struct Cat : Animal {};

register_class(Animal);
register_class(Dog, Animal);
register_class(Cat, Animal);

declare_method(std::string, speak, (virtual_<Animal&>));

define_method(std::string, speak, (Animal&)) {
    return "...";
}

define_method(std::string, speak, (Dog&)) {
    return "woof";
}

define_method(std::string, speak, (Cat&)) {
    return "meow";
}

int main() {
    yorel::yomm2::update_methods();

    Dog dog;
    Cat cat;
    Animal animal;

    const std::string d = speak(dog);
    const std::string c = speak(cat);
    const std::string a = speak(animal);

    std::cout << "dog  -> " << d << "\n";
    std::cout << "cat  -> " << c << "\n";
    std::cout << "base -> " << a << "\n";

    if (d != "woof" || c != "meow" || a != "...") {
        std::cerr << "dispatch mismatch\n";
        return 1;
    }
    std::cout << "dispatch OK\n";
    return 0;
}