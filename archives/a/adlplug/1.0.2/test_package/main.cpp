#include <opl3/adl/player.h>

#include <iostream>

int main()
{
    const auto emulators = Player::enumerate_emulators();
    if (emulators.empty()) {
        std::cerr << "ADLMIDI exposes no emulators\n";
        return 1;
    }

    Player player;
    // Player::init is void in ADLplug v1.0.2; the state change is verified by
    // set_num_chips() and num_chips() immediately below.
    player.init(44100);
    if (!player.set_num_chips(1) || player.num_chips() == 0) {
        std::cerr << "ADLMIDI player chip setup failed\n";
        return 1;
    }

    std::cout << "ADLplug core initialized with " << emulators.front() << '\n';
    return 0;
}
