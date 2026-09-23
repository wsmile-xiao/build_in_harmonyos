#include <iostream>
#include <string>

#include <mqtt/connect_options.h>
#include <mqtt/message.h>

int main() {
    mqtt::connect_options options;
    options.set_clean_session(true);

    auto message = mqtt::make_message("conan/paho.mqtt.cpp", "payload");
    message->set_qos(1);

    if (message->get_topic() != "conan/paho.mqtt.cpp") {
        std::cerr << "unexpected MQTT topic\n";
        return 1;
    }
    if (message->get_payload_str() != "payload") {
        std::cerr << "unexpected MQTT payload\n";
        return 1;
    }
    if (message->get_qos() != 1) {
        std::cerr << "unexpected MQTT QoS\n";
        return 1;
    }

    std::cout << "paho.mqtt.cpp API/link test: OK\n";
    return 0;
}
