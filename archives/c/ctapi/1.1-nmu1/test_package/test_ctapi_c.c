#include <ctapi.h>

#include <stdint.h>

int main(void)
{
    uint8_t destination = CT;
    uint8_t source = HOST;
    uint8_t command[] = {0x20U, 0x13U, 0x00U, 0x00U};
    uint8_t response[8] = {0U};
    uint16_t response_length = (uint16_t)sizeof(response);

    if (CT_init(7U, 1U) != OK) {
        return 1;
    }
    if (CT_data(7U, &destination, &source,
                (uint16_t)sizeof(command), command,
                &response_length, response) != OK) {
        return 2;
    }
    if (destination != HOST || source != CT) {
        return 3;
    }
    if (response_length != 2U || response[0] != 0x90U || response[1] != 0x00U) {
        return 4;
    }
    if (CT_close(7U) != OK) {
        return 5;
    }
    if (ERR_INVALID != -1 || ERR_TRANS != -10 || ERR_HOST != -127) {
        return 6;
    }
    if (ICC1 != 0x00 || ICC7 != 0x07 || ICC14 != 0x0e) {
        return 7;
    }
    return 0;
}
