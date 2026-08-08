#include <SFML/Network/Packet.hpp>
#include <SFML/System/Clock.hpp>
#include <SFML/System/Time.hpp>

#include <cstdint>
#include <string>

int main()
{
    sf::Clock clock;
    sf::Packet packet;
    const std::int32_t expectedNumber = 2601;
    const std::string expectedText = "HarmonyOS";
    packet << expectedNumber << expectedText;

    std::int32_t actualNumber = 0;
    std::string actualText;
    packet >> actualNumber >> actualText;

    if (actualNumber != expectedNumber || actualText != expectedText)
        return 1;

    return clock.getElapsedTime() >= sf::Time::Zero ? 0 : 2;
}
