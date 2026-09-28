using byte = unsigned char;
using vec_t = float;
using vec3_t = vec_t[3];

#include <qwprot/protocol.h>

namespace {

int failures = 0;

void check(bool condition)
{
    if (!condition) {
        ++failures;
    }
}

} // namespace

int main()
{
    check(PROTOCOL_VERSION == 28);
    check(PORT_MASTER == 27000);
    check(PORT_CLIENT == 27001);
    check(PORT_SERVER == 27500);
    check(PORT_QUAKETV == 27900);
    check(CLIENT_EXTENSIONS == SERVER_EXTENSIONS);
    check((CLIENT_EXTENSIONS & Z_EXT_PM_TYPE_NEW) != 0);
    check((CLIENT_EXTENSIONS & Z_EXT_PF_SOLID) != 0);
    check(UPDATE_BACKUP == 64);
    check(UPDATE_MASK == 63);
    check(MAX_CLIENTS == 32);
    check(MAX_MVD_PACKET_ENTITIES >= MAX_PEXT256_PACKET_ENTITIES);

    usercmd_t command{};
    command.msec = 16;
    command.forwardmove = 200;
    command.buttons = BUTTON_ATTACK | BUTTON_JUMP;
    check(command.msec == 16);
    check(command.forwardmove == 200);
    check((command.buttons & BUTTON_ATTACK) != 0 &&
          (command.buttons & BUTTON_JUMP) != 0);

    return failures;
}
