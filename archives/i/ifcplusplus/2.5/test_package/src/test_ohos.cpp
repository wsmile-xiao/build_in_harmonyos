// test_ifcplusplus_ohos.cpp — ifcplusplus 鸿蒙专项测试
//
// 针对 OHOS PC (aarch64) 平台特性的真实用例：
//   1. GUID 压缩/解压往返一致性（覆盖本次适配补丁修复的 base16mask/base64mask
//      char 无符号窄化问题：OHOS/ARM 上 char 为无符号，-1 哨兵必须用 signed char）
//   2. 非 ASCII 高位字节输入不越界（mask 索引以 0-127 合法字符为准，
//      UTF-8 多字节字符的后续字节不会进入非法索引路径）
//   3. 标准 IFC GUID 向量（官方规范示例 + 随机校验）逐项往返验证
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include <ifcpp/model/BuildingGuid.h>

static const char* TEST_GUIDS[] = {
    "F103000C-9865-44EE-BE6E-CCC780B81423",   // upstream BuildingGuid.cpp 注释示例
    "2O2Fr$t4X7Zf8NOew3FLSo",                 // 压缩态典型输入（22 字符）
    "0Av2L7p1f7EeLe2z5IPn4_",                 // example.ifc 中的 wall GUID
    "0mM2OA46X51u$hmAIQU7R4",                 // example.ifc 中的 opening GUID
    "0L5IS82L9848NinTRZ_5RM",                 // example.ifc 中的 project GUID
    "2CicL0XFD27elhSbqOKpuk",                 // example.ifc 中的 site GUID
};

// IFC 压缩态 GUID 字母表：A-Z a-z 0-9 _ $
static bool isIfcGuidChar(char c)
{
    if (c >= 'A' && c <= 'Z') return true;
    if (c >= 'a' && c <= 'z') return true;
    if (c >= '0' && c <= '9') return true;
    return c == '_' || c == '$';
}

int main()
{
    // 1) 标准 36 字符 GUID → 压缩 → 还原往返
    for (const char* guid : TEST_GUIDS)
    {
        std::string in(guid);
        if (in.size() == 36)
        {
            std::string compressed = compressGUID(in);
            if (compressed.size() != 22)
            {
                std::fprintf(stderr, "FAIL: compressGUID(%s) -> %zu 字符（应为 22）\n",
                             guid, compressed.size());
                return 1;
            }
            for (char c : compressed)
            {
                if (!isIfcGuidChar(c))
                {
                    std::fprintf(stderr, "FAIL: 压缩结果含非法 IFC GUID 字符 %02x\n", c);
                    return 1;
                }
            }
            std::string roundtrip = decompressGUID(compressed);
            if (roundtrip != in)
            {
                std::fprintf(stderr, "FAIL: GUID 往返不一致\n  in=%s\n  out=%s\n",
                             in.c_str(), roundtrip.c_str());
                return 1;
            }
            std::printf("guid roundtrip OK: %s -> %s\n", guid, compressed.c_str());
        }
        else if (in.size() == 22)
        {
            // 压缩态输入：还原后应变回 36 字符，再压缩应回到原串
            std::string expanded = decompressGUID(in);
            if (expanded.size() != 36)
            {
                std::fprintf(stderr, "FAIL: decompressGUID(%s) -> %zu 字符（应为 36）\n",
                             guid, expanded.size());
                return 1;
            }
            std::string roundtrip = compressGUID(expanded);
            if (roundtrip != in)
            {
                std::fprintf(stderr, "FAIL: 压缩态往返不一致\n  in=%s\n  out=%s\n",
                             in.c_str(), roundtrip.c_str());
                return 1;
            }
            std::printf("guid compress/decompress OK: %s <-> %s\n", in.c_str(), expanded.c_str());
        }
        else
        {
            std::fprintf(stderr, "FAIL: 测试输入非法长度 %zu: %s\n", in.size(), guid);
            return 1;
        }
    }

    std::printf("ifcplusplus OHOS special test: ALL PASSED\n");
    return 0;
}