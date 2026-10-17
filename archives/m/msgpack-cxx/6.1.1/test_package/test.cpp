#include <msgpack.hpp>
#include <string>
#include <iostream>
#include <cassert>

int main(void)
{
    // Pack/unpack an integer
    int src = 42;
    msgpack::sbuffer sbuf;
    msgpack::pack(sbuf, src);

    msgpack::object_handle oh = msgpack::unpack(sbuf.data(), sbuf.size());
    int dst = oh.get().as<int>();
    assert(dst == 42);

    // Pack/unpack a string
    std::string str_src = "hello msgpack";
    msgpack::sbuffer sbuf2;
    msgpack::pack(sbuf2, str_src);

    msgpack::object_handle oh2 = msgpack::unpack(sbuf2.data(), sbuf2.size());
    std::string dst_str = oh2.get().as<std::string>();
    assert(dst_str == "hello msgpack");

    // Pack/unpack a vector
    std::vector<int> vec_src = {1, 2, 3};
    msgpack::sbuffer sbuf3;
    msgpack::pack(sbuf3, vec_src);

    msgpack::object_handle oh3 = msgpack::unpack(sbuf3.data(), sbuf3.size());
    std::vector<int> vec_dst = oh3.get().as<std::vector<int>>();
    assert(vec_dst.size() == 3);
    assert(vec_dst[0] == 1);
    assert(vec_dst[1] == 2);
    assert(vec_dst[2] == 3);

    std::cout << "msgpack-cxx test passed" << std::endl;
    return 0;
}
