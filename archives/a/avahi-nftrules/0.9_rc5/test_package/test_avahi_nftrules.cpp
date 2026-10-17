#include <iostream>
#include <fstream>
#include <cstdlib>
#include <string>

int main() {
    // 从环境变量获取 nftables 规则文件路径
    const char* rules_path = std::getenv("AVAHI_NFT_RULES");
    if (!rules_path) {
        std::cerr << "Error: AVAHI_NFT_RULES environment variable not set" << std::endl;
        return 1;
    }
    
    std::cout << "Checking nftables rules at: " << rules_path << std::endl;
    
    // 构建完整文件路径
    std::string nft_file = std::string(rules_path) + "/50_avahi.nft";
    
    // 检查文件是否存在
    std::ifstream file(nft_file);
    if (!file.good()) {
        std::cerr << "Error: 50_avahi.nft not found at " << nft_file << std::endl;
        return 1;
    }
    
    // 读取并验证文件内容
    std::string line;
    bool found_port_5353 = false;
    bool found_avahi = false;
    
    while (std::getline(file, line)) {
        if (line.find("5353") != std::string::npos) {
            found_port_5353 = true;
        }
        if (line.find("Avahi") != std::string::npos || line.find("avahi") != std::string::npos) {
            found_avahi = true;
        }
    }
    file.close();
    
    if (!found_port_5353) {
        std::cerr << "Error: mDNS port 5353 not found in rules" << std::endl;
        return 1;
    }
    
    if (!found_avahi) {
        std::cerr << "Error: Avahi reference not found in rules" << std::endl;
        return 1;
    }
    
    std::cout << "✓ avahi-nftrules package validated successfully" << std::endl;
    std::cout << "✓ Found rule for UDP port 5353 (mDNS)" << std::endl;
    std::cout << "✓ File location: " << nft_file << std::endl;
    
    return 0;
}
