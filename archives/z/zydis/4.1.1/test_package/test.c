#include <stdio.h>
#include <string.h>

#include <Zydis/Zydis.h>

static int check_decoder(void)
{
    ZyanU8 data[] =
    {
        0x51, 0x8D, 0x45, 0xFF, 0x50, 0xFF, 0x75, 0x0C, 0xFF, 0x75,
        0x08, 0xFF, 0x15, 0xA0, 0xA5, 0x48, 0x76, 0x85, 0xC0, 0x0F,
        0x88, 0xFC, 0xDA, 0x02, 0x00
    };
    ZyanU64 runtime_address = 0x007FFFFFFF400000;
    ZyanUSize offset = 0;
    int count = 0;
    ZydisDisassembledInstruction instruction;

    while (ZYAN_SUCCESS(ZydisDisassembleIntel(
        ZYDIS_MACHINE_MODE_LONG_64, runtime_address,
        data + offset, sizeof(data) - offset, &instruction)))
    {
        if (count == 0)
        {
            if (instruction.info.mnemonic != ZYDIS_MNEMONIC_PUSH)
            {
                printf("first instruction mnemonic mismatch\n");
                return 1;
            }
            if (instruction.info.length != 1)
            {
                printf("first instruction length mismatch\n");
                return 2;
            }
            if (strstr(instruction.text, "push") == NULL &&
                strstr(instruction.text, "PUSH") == NULL)
            {
                printf("first instruction text mismatch: %s\n", instruction.text);
                return 3;
            }
        }
        offset += instruction.info.length;
        runtime_address += instruction.info.length;
        ++count;
    }
    if (offset != sizeof(data))
    {
        printf("decoded %u of %u bytes\n", (unsigned)offset, (unsigned)sizeof(data));
        return 4;
    }
    if (count != 8)
    {
        printf("instruction count mismatch: %d\n", count);
        return 5;
    }
    printf("decoder/formatter check passed: %d instructions\n", count);
    return 0;
}

static int check_encoder(void)
{
    ZydisEncoderRequest req;
    ZyanU8 encoded[ZYDIS_MAX_INSTRUCTION_LENGTH];
    ZyanUSize encoded_length = sizeof(encoded);
    static const ZyanU8 expected[] = { 0x48, 0xC7, 0xC0, 0x37, 0x13, 0x00, 0x00 };
    ZyanUSize i;

    memset(&req, 0, sizeof(req));
    req.mnemonic = ZYDIS_MNEMONIC_MOV;
    req.machine_mode = ZYDIS_MACHINE_MODE_LONG_64;
    req.operand_count = 2;
    req.operands[0].type = ZYDIS_OPERAND_TYPE_REGISTER;
    req.operands[0].reg.value = ZYDIS_REGISTER_RAX;
    req.operands[1].type = ZYDIS_OPERAND_TYPE_IMMEDIATE;
    req.operands[1].imm.u = 0x1337;

    if (ZYAN_FAILED(ZydisEncoderEncodeInstruction(&req, encoded, &encoded_length)))
    {
        printf("encoder request failed\n");
        return 6;
    }
    if (encoded_length != sizeof(expected))
    {
        printf("encoded length mismatch: %u\n", (unsigned)encoded_length);
        return 7;
    }
    for (i = 0; i < sizeof(expected); ++i)
    {
        if (encoded[i] != expected[i])
        {
            printf("encoded byte %u mismatch\n", (unsigned)i);
            return 8;
        }
    }
    printf("encoder check passed: %u bytes\n", (unsigned)encoded_length);
    return 0;
}

int main(void)
{
    int rc;

    if (ZydisGetVersion() != ZYDIS_VERSION)
    {
        printf("version macro mismatch\n");
        return 9;
    }
    rc = check_decoder();
    if (rc != 0)
    {
        return rc;
    }
    rc = check_encoder();
    if (rc != 0)
    {
        return rc;
    }
    puts("zydis consumer test passed");
    return 0;
}
