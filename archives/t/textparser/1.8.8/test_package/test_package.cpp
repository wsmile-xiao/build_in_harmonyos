#include <iostream>
#include "TextParser.h"

int main() {
    // 测试 TextParser singleton 模式
    TextParser* tp = TextParser::get_instance_singleton();
    
    if (tp == nullptr) {
        std::cerr << "Failed to get TextParser instance" << std::endl;
        return 1;
    }
    
    std::cout << "TextParser instance created successfully" << std::endl;
    
    // 测试版本信息
    std::cout << "TextParser version: " << TP_VERSION << std::endl;
    
    // 测试基本状态
    tp->status();
    
    std::cout << "TextParser test passed" << std::endl;
    return 0;
}
