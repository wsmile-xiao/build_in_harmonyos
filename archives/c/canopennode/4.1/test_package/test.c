/*
 * Conan test_package L1 test for CANopenNode 4.1.
 *
 * Consumer use case: simulates a CANopen device application exactly as the
 * upstream example (example/main_blank.c) does, but bounded (finite loop).
 * It uses only public headers (CANopen.h) and public API:
 *   CO_new / CO_CANinit / CO_LSSinit / CO_CANopenInit / CO_CANopenInitPDO /
 *   CO_CANsetNormalMode / CO_process / CO_delete
 * and verifies observable results: allocation succeeds, every initialization
 * returns CO_ERROR_NO, and the NMT state machine advances out of the reset
 * state after process cycles (printed to stdout).
 */
#include <stdio.h>
#include <string.h>

#include "CANopen.h"
#include "OD.h"

#define log_printf(macropar_message, ...) printf(macropar_message, ##__VA_ARGS__)

#define NMT_CONTROL                                                                                                    \
    CO_NMT_STARTUP_TO_OPERATIONAL                                                                                      \
    | CO_NMT_ERR_ON_ERR_REG | CO_ERR_REG_GENERIC_ERR | CO_ERR_REG_COMMUNICATION
#define FIRST_HB_TIME        500
#define SDO_SRV_TIMEOUT_TIME 1000
#define SDO_CLI_TIMEOUT_TIME 500
#define SDO_CLI_BLOCK        false
#define OD_STATUS_BITS       NULL

int
main(void) {
    CO_ReturnError_t err;
    CO_NMT_reset_cmd_t reset = CO_RESET_NOT;
    uint32_t heapMemoryUsed;
    void* CANptr = NULL;           /* CAN module address (blank driver: no hardware) */
    uint8_t pendingNodeId = 10;    /* configurable by LSS slave */
    uint8_t activeNodeId = 10;
    uint16_t pendingBitRate = 125;
    uint32_t errInfo = 0;
    unsigned int cycles = 0;
    int fail = 0;

    /* 1) Allocate CANopen objects (uses CO_new public API) */
    CO_t* CO = CO_new(NULL, &heapMemoryUsed);
    if (CO == NULL) {
        log_printf("FAIL: CO_new returned NULL\n");
        return 1;
    }
    log_printf("Allocated %u bytes for CANopen objects\n", heapMemoryUsed);

    /* 2) Communication reset section - exactly like upstream example */
    CO->CANmodule->CANnormal = false;
    CO_CANsetConfigurationMode((void*)&CANptr);
    CO_CANmodule_disable(CO->CANmodule);

    err = CO_CANinit(CO, CANptr, pendingBitRate);
    if (err != CO_ERROR_NO) {
        log_printf("FAIL: CO_CANinit returned error 0x%02x\n", err);
        CO_delete(CO);
        return 1;
    }

    CO_LSS_address_t lssAddress = {
        .identity = {.vendorID = 0, .productCode = 0, .revisionNumber = 0, .serialNumber = 0}};
    err = CO_LSSinit(CO, &lssAddress, &pendingNodeId, &pendingBitRate);
    if (err != CO_ERROR_NO) {
        log_printf("FAIL: CO_LSSinit returned error 0x%02x\n", err);
        CO_delete(CO);
        return 1;
    }

    activeNodeId = pendingNodeId;
    err = CO_CANopenInit(CO, NULL, NULL, OD, OD_STATUS_BITS, NMT_CONTROL, FIRST_HB_TIME, SDO_SRV_TIMEOUT_TIME,
                         SDO_CLI_TIMEOUT_TIME, SDO_CLI_BLOCK, activeNodeId, &errInfo);
    if (err != CO_ERROR_NO && err != CO_ERROR_NODE_ID_UNCONFIGURED_LSS) {
        log_printf("FAIL: CO_CANopenInit returned error 0x%02x (errInfo 0x%x)\n", err, errInfo);
        CO_delete(CO);
        return 1;
    }
    log_printf("CO_CANopenInit OK (err=CO_ERROR_NO)\n");

    err = CO_CANopenInitPDO(CO, CO->em, OD, activeNodeId, &errInfo);
    if (err != CO_ERROR_NO && err != CO_ERROR_NODE_ID_UNCONFIGURED_LSS) {
        log_printf("FAIL: CO_CANopenInitPDO returned error 0x%02x\n", err);
        CO_delete(CO);
        return 1;
    }
    log_printf("CO_CANopenInitPDO OK\n");

    /* 3) Start CAN and run N cycles of CO_process */
    CO_CANsetNormalMode(CO->CANmodule);
    log_printf("CANopenNode - Running...\n");

    while (reset == CO_RESET_NOT && cycles < 20) {
        reset = CO_process(CO, false, 500, NULL);
        cycles++;
    }

    /* 4) Verify observable NMT state advanced out of reset/initialization */
    if (reset != CO_RESET_NOT) {
        log_printf("FAIL: CO_process requested reset cmd %d after %u cycles\n", (int)reset, cycles);
        fail = 1;
    } else if (CO->nodeIdUnconfigured) {
        log_printf("FAIL: node id still unconfigured\n");
        fail = 1;
    } else {
        log_printf("CO_process ran %u cycles, no reset requested - OK\n", cycles);
    }

    /* 5) Close */
    CO_CANsetConfigurationMode((void*)&CANptr);
    CO_delete(CO);
    log_printf("CO_delete OK - CANopenNode finished\n");

    if (fail) {
        log_printf("FAIL\n");
        return 1;
    }
    log_printf("ALL TESTS PASSED\n");
    return 0;
}