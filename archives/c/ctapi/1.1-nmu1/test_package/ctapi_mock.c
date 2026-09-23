#include <ctapi.h>

#include <stddef.h>

static uint16_t active_terminal;

int8_t CT_init(uint16_t logical_terminal_number, uint16_t physical_interface)
{
    if (physical_interface != 1U) {
        return ERR_INVALID;
    }
    active_terminal = logical_terminal_number;
    return OK;
}
int8_t CT_data(
    uint16_t logical_terminal_number,
    uint8_t *destination_address,
    uint8_t *source_address,
    uint16_t command_length,
    uint8_t *command,
    uint16_t *response_length,
    uint8_t *response)
{
    if (logical_terminal_number != active_terminal ||
        destination_address == NULL || source_address == NULL ||
        command == NULL || response_length == NULL || response == NULL) {
        return ERR_INVALID;
    }
    if (*destination_address != CT || *source_address != HOST ||
        command_length != 4U || *response_length < 2U ||
        command[0] != 0x20U || command[1] != 0x13U) {
        return ERR_TRANS;
    }

    *destination_address = HOST;
    *source_address = CT;
    response[0] = 0x90U;
    response[1] = 0x00U;
    *response_length = 2U;
    return OK;
}

int8_t CT_close(uint16_t logical_terminal_number)
{
    if (logical_terminal_number != active_terminal) {
        return ERR_CT;
    }
    active_terminal = 0U;
    return OK;
}
