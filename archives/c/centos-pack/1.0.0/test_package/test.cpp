// R34: 实质性测试 - 调用 CentPack 的 doublearray1d 类
#include <iostream>
#include "doublearray1d.h"  // CentPack 的一维数组类

int main() {
    std::cout << "Testing centos-pack 1.0.0 doublearray1d class..." << std::endl;
    
    // 创建一个一维数组对象并初始化
    doublearray1d arr(5);  // 创建长度为 5 的数组
    
    // 设置数组元素
    for(long i = 0; i < 5; i++) {
        arr(i) = i * 2.0;  // 使用 operator() 访问
    }
    
    // 读取并验证
    std::cout << "Array[2] = " << arr(2) << " (expected 4.0)" << std::endl;
    
    if (arr(2) == 4.0) {
        std::cout << "centos-pack test: PASSED" << std::endl;
        return 0;
    } else {
        std::cerr << "centos-pack test: FAILED" << std::endl;
        return 1;
    }
}
