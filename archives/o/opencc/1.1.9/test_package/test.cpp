#include <opencc/SimpleConverter.hpp>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char* argv[]) {
    std::vector<std::string> paths;
    if (argc > 1) {
        paths.push_back(argv[1]);
    }

    try {
        opencc::SimpleConverter converter("s2t.json", paths);
        // "简体中文" in UTF-8
        std::string input = "\xe7\xae\x80\xe4\xbd\x93\xe4\xb8\xad\xe6\x96\x87";
        std::string output = converter.Convert(input);

        if (output.empty() || output == input) {
            std::cerr << "Test FAILED: conversion did not produce expected output" << std::endl;
            return 1;
        }

        std::cout << "Input: " << input << std::endl;
        std::cout << "Output: " << output << std::endl;
        std::cout << "Test PASSED" << std::endl;
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "Test FAILED: " << e.what() << std::endl;
        return 1;
    }
}
