#include <zmq.hpp>
#include <zmq_addon.hpp>
#include <cassert>
#include <iostream>
#include <vector>

int main(void) {
    // Test basic context creation
    zmq::context_t ctx(1);
    assert(ctx.handle() != nullptr);

    // Test socket creation
    zmq::socket_t sock(ctx, zmq::socket_type::rep);
    sock.bind("inproc://test");

    // Test socket operations
    zmq::socket_t client(ctx, zmq::socket_type::req);
    client.connect("inproc://test");

    // Send a message
    std::string msg_str = "Hello ZeroMQ";
    zmq::message_t msg(msg_str.begin(), msg_str.end());
    client.send(msg, zmq::send_flags::none);

    // Receive the message
    zmq::message_t received;
    sock.recv(received, zmq::recv_flags::none);
    assert(received.to_string() == msg_str);

    // Test zmq_addon (multipart)
    std::vector<zmq::message_t> msgs;
    msgs.emplace_back(zmq::message_t("part1"));
    msgs.emplace_back(zmq::message_t("part2"));
    auto send_result = zmq::send_multipart(sock, std::move(msgs));
    assert(send_result.has_value());

    std::vector<zmq::message_t> recv_msgs;
    auto recv_result = zmq::recv_multipart(client, std::back_inserter(recv_msgs));
    assert(recv_result.has_value());
    assert(recv_msgs.size() == 2);

    std::cout << "cppzmq test passed! All assertions OK." << std::endl;
    return 0;
}
