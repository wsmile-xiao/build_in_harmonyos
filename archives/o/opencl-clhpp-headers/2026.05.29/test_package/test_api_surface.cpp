// test_api_surface.cpp — Verify key API methods and enums are declared
#include <CL/opencl.hpp>
#include <type_traits>

int main() {
    // Verify cl::QueueProperties enum exists (used for CommandQueue construction)
    {
        cl::QueueProperties qp = cl::QueueProperties::None;
        (void)qp;
    }

    // Verify device fission enum exists
    {
        cl_device_affinity_domain ad = CL_DEVICE_AFFINITY_DOMAIN_NUMA;
        (void)ad;
    }

    // Verify cl_bool type is available (from C headers)
    {
        cl_bool b = CL_TRUE;
        (void)b;
    }

    // Verify cl_command_queue_properties type
    {
        cl_command_queue_properties p = CL_QUEUE_OUT_OF_ORDER_EXEC_MODE_ENABLE;
        (void)p;
    }

    // Verify cl_mem_flags type
    {
        cl_mem_flags f = CL_MEM_READ_WRITE;
        (void)f;
    }

    // Verify cl_map_flags type
    {
        cl_map_flags f = CL_MAP_READ;
        (void)f;
    }

    // Verify cl_profiling_info type
    {
        cl_profiling_info pi = CL_PROFILING_COMMAND_QUEUED;
        (void)pi;
    }

    // Verify string type used by the API
    {
        cl::string s = "test";
        (void)s;
    }

    // Verify cl::NDRange is available
    {
        cl::NDRange range(1);
        (void)range;
    }

    return 0;
}
