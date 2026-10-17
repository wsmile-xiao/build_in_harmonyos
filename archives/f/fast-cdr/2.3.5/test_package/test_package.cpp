#include <fastcdr/FastBuffer.h>
#include <fastcdr/Cdr.h>

#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>

// 消费者测试：使用 fastcdr 实际 API 做序列化/反序列化往返
int main() {
    // 1) 构造 payload 缓冲
    constexpr uint32_t payload_size = 64;
    char buffer[payload_size] = {0};
    eprosima::fastcdr::FastBuffer fastbuffer(buffer, payload_size);

    // 2) 序列化：写入 uint32 + 字符串
    {
        eprosima::fastcdr::Cdr cdr(fastbuffer, eprosima::fastcdr::Cdr::DEFAULT_ENDIAN,
                                   eprosima::fastcdr::CdrVersion::DDS_CDR);
        uint32_t value = 0x12345678U;
        cdr.serialize(value);
        const char* text = "fast-cdr-consumer-test";
        cdr.serialize(text);
        assert(cdr.getSerializedDataLength() > 0);
    }

    // 3) 反序列化：读回并校验
    {
        eprosima::fastcdr::Cdr cdr(fastbuffer, eprosima::fastcdr::Cdr::DEFAULT_ENDIAN,
                                   eprosima::fastcdr::CdrVersion::DDS_CDR);
        uint32_t value = 0;
        cdr.deserialize(value);
        std::string text;
        cdr.deserialize(text);
        assert(value == 0x12345678U);
        assert(text == "fast-cdr-consumer-test");
    }

    std::cout << "fast-cdr consumer test: OK" << std::endl;
    return 0;
}
