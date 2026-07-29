#include <ittnotify.h>
#include <jitprofiling.h>

int main(void)
{
    __itt_domain *domain = __itt_domain_create("ohpcd.ittapi.consumer");
    __itt_string_handle *name = __itt_string_handle_create("smoke-task");

    if (domain != 0 && name != 0) {
        __itt_task_begin(domain, __itt_null, __itt_null, name);
        __itt_task_end(domain);
    }

    iJIT_IsProfilingActiveFlags status = iJIT_IsProfilingActive();
    return status == iJIT_NOTHING_RUNNING || status == iJIT_SAMPLING_ON
        ? 0
        : 1;
}
