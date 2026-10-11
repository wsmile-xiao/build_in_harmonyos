// SPDX-License-Identifier: LGPL-2.1-or-later
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include <hinawa.h>

static int check_property(GObject *object, const char *name)
{
    return g_object_class_find_property(G_OBJECT_GET_CLASS(object), name) != NULL;
}
static int test_fw_node(void)
{
    HinawaFwNode *node = hinawa_fw_node_new();
    int ok = node != NULL && HINAWA_IS_FW_NODE(node) &&
             check_property(G_OBJECT(node), "generation") &&
             g_signal_lookup("bus-update", HINAWA_TYPE_FW_NODE) != 0 &&
             g_signal_lookup("disconnected", HINAWA_TYPE_FW_NODE) != 0;
    g_clear_object(&node);
    return ok;
}

static int test_fw_req(void)
{
    HinawaFwReq *request = hinawa_fw_req_new();
    int ok = request != NULL && HINAWA_IS_FW_REQ(request) &&
             g_signal_lookup("responded", HINAWA_TYPE_FW_REQ) != 0;
    g_clear_object(&request);
    return ok;
}

static int test_fw_resp(void)
{
    HinawaFwResp *response = hinawa_fw_resp_new();
    int ok = response != NULL && HINAWA_IS_FW_RESP(response) &&
             check_property(G_OBJECT(response), "is-reserved") &&
             check_property(G_OBJECT(response), "offset") &&
             check_property(G_OBJECT(response), "width") &&
             g_signal_lookup("requested", HINAWA_TYPE_FW_RESP) != 0;
    g_clear_object(&response);
    return ok;
}

static int test_fw_fcp(void)
{
    HinawaFwFcp *fcp = hinawa_fw_fcp_new();
    int ok = fcp != NULL && HINAWA_IS_FW_FCP(fcp) &&
             g_type_is_a(HINAWA_TYPE_FW_FCP, HINAWA_TYPE_FW_RESP) &&
             check_property(G_OBJECT(fcp), "is-bound") &&
             g_signal_lookup("responded", HINAWA_TYPE_FW_FCP) != 0;
    g_clear_object(&fcp);
    return ok;
}

static int test_cycle_time(void)
{
    HinawaCycleTime *cycle_time = hinawa_cycle_time_new();
    guint16 fields[3] = {1, 1, 1};
    guint isoc_cycle[2] = {0, 0};
    guint32 raw = 1;
    gint64 seconds = 1;
    gint32 nanoseconds = 1;
    gint clock_id = 1;
    int ok;

    if (cycle_time == NULL)
        return 0;
    hinawa_cycle_time_get_system_time(cycle_time, &seconds, &nanoseconds);
    hinawa_cycle_time_get_clock_id(cycle_time, &clock_id);
    hinawa_cycle_time_get_fields(cycle_time, fields);
    hinawa_cycle_time_get_raw(cycle_time, &raw);
    hinawa_cycle_time_parse_tstamp(0xe123, isoc_cycle);
    ok = seconds == 0 && nanoseconds == 0 && clock_id == 0 && raw == 0 &&
         fields[0] == 0 && fields[1] == 0 && fields[2] == 0 &&
         isoc_cycle[0] == 7 && isoc_cycle[1] == 0x123;
    g_boxed_free(HINAWA_TYPE_CYCLE_TIME, cycle_time);
    return ok;
}

static int test_enums(void)
{
    return G_TYPE_IS_ENUM(hinawa_fw_tcode_get_type()) &&
           G_TYPE_IS_ENUM(hinawa_fw_rcode_get_type()) &&
           G_TYPE_IS_ENUM(hinawa_fw_req_error_get_type()) &&
           G_TYPE_IS_ENUM(hinawa_fw_node_error_get_type()) &&
           G_TYPE_IS_ENUM(hinawa_fw_resp_error_get_type()) &&
           G_TYPE_IS_ENUM(hinawa_fw_fcp_error_get_type()) &&
           HINAWA_FW_TCODE_WRITE_QUADLET_REQUEST == TCODE_WRITE_QUADLET_REQUEST &&
           HINAWA_FW_RCODE_COMPLETE == RCODE_COMPLETE;
}

static int test_functions(void)
{
    return hinawa_fw_node_error_quark() != 0 &&
           hinawa_fw_req_error_quark() != 0 &&
           hinawa_fw_resp_error_quark() != 0 &&
           hinawa_fw_fcp_error_quark() != 0;
}

static int test_ohos_aarch64_abi(void)
{
    guint parsed[2] = {0, 0};
    hinawa_cycle_time_parse_tstamp(0xa456, parsed);
    return sizeof(void *) == 8 && sizeof(guint) == 4 && sizeof(guint64) == 8 &&
           G_BYTE_ORDER == G_LITTLE_ENDIAN && parsed[0] == 5 && parsed[1] == 0x456;
}

int main(int argc, char **argv)
{
    int selected;
    int passed = 0;

    if (argc != 2)
        return EXIT_FAILURE;
    selected = atoi(argv[1]);
    switch (selected) {
    case 1: passed = test_fw_node(); break;
    case 2: passed = test_fw_req(); break;
    case 3: passed = test_fw_resp(); break;
    case 4: passed = test_fw_fcp(); break;
    case 5: passed = test_cycle_time(); break;
    case 6: passed = test_enums(); break;
    case 7: passed = test_functions(); break;
    case 8: passed = test_ohos_aarch64_abi(); break;
    default: return EXIT_FAILURE;
    }
    if (!passed) {
        fprintf(stderr, "libhinawa test %d failed\n", selected);
        return EXIT_FAILURE;
    }
    printf("libhinawa test %d passed\n", selected);
    return EXIT_SUCCESS;
}
