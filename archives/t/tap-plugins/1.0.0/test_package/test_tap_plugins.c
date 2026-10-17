#include <dirent.h>
#include <dlfcn.h>
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

#include <ladspa.h>

#define FRAME_COUNT 64UL
#define EXPECTED_MODULES 19U

typedef const LADSPA_Descriptor *(*descriptor_fn)(unsigned long);

static int compare_names(const void *left, const void *right) {
    const char *const *a = left;
    const char *const *b = right;
    return strcmp(*a, *b);
}

static LADSPA_Data default_control(const LADSPA_PortRangeHint *hint,
                                   unsigned long sample_rate) {
    LADSPA_Data lower = hint->LowerBound;
    LADSPA_Data upper = hint->UpperBound;
    const LADSPA_PortRangeHintDescriptor bits = hint->HintDescriptor;
    const LADSPA_PortRangeHintDescriptor value = bits & LADSPA_HINT_DEFAULT_MASK;

    if (LADSPA_IS_HINT_SAMPLE_RATE(bits)) {
        lower *= (LADSPA_Data)sample_rate;
        upper *= (LADSPA_Data)sample_rate;
    }
    if (value == LADSPA_HINT_DEFAULT_MINIMUM) return lower;
    if (value == LADSPA_HINT_DEFAULT_LOW) return lower * 0.75f + upper * 0.25f;
    if (value == LADSPA_HINT_DEFAULT_MIDDLE) return (lower + upper) * 0.5f;
    if (value == LADSPA_HINT_DEFAULT_HIGH) return lower * 0.25f + upper * 0.75f;
    if (value == LADSPA_HINT_DEFAULT_MAXIMUM) return upper;
    if (value == LADSPA_HINT_DEFAULT_0) return 0.0f;
    if (value == LADSPA_HINT_DEFAULT_1) return 1.0f;
    if (value == LADSPA_HINT_DEFAULT_100) return 100.0f;
    if (value == LADSPA_HINT_DEFAULT_440) return 440.0f;
    if (LADSPA_IS_HINT_BOUNDED_BELOW(bits) && LADSPA_IS_HINT_BOUNDED_ABOVE(bits)) {
        return (lower + upper) * 0.5f;
    }
    if (LADSPA_IS_HINT_BOUNDED_BELOW(bits)) return lower;
    if (LADSPA_IS_HINT_BOUNDED_ABOVE(bits)) return upper;
    return 0.0f;
}

static int run_descriptor(const LADSPA_Descriptor *descriptor) {
    const unsigned long rate = 48000UL;
    LADSPA_Handle instance;
    LADSPA_Data **ports;
    unsigned long port;
    unsigned long frame;
    int result = 0;

    if (descriptor == NULL || descriptor->Label == NULL ||
        descriptor->Name == NULL || descriptor->Maker == NULL ||
        descriptor->instantiate == NULL || descriptor->connect_port == NULL ||
        descriptor->run == NULL || descriptor->cleanup == NULL ||
        descriptor->PortCount == 0) {
        fprintf(stderr, "invalid LADSPA descriptor\n");
        return 1;
    }

    instance = descriptor->instantiate(descriptor, rate);
    if (instance == NULL) {
        fprintf(stderr, "%s: instantiate failed\n", descriptor->Label);
        return 1;
    }

    ports = calloc(descriptor->PortCount, sizeof(*ports));
    if (ports == NULL) {
        descriptor->cleanup(instance);
        return 1;
    }
    for (port = 0; port < descriptor->PortCount; ++port) {
        size_t count = LADSPA_IS_PORT_AUDIO(descriptor->PortDescriptors[port])
                           ? FRAME_COUNT : 1UL;
        ports[port] = calloc(count, sizeof(**ports));
        if (ports[port] == NULL) {
            result = 1;
            break;
        }
        if (LADSPA_IS_PORT_CONTROL(descriptor->PortDescriptors[port]) &&
            LADSPA_IS_PORT_INPUT(descriptor->PortDescriptors[port])) {
            ports[port][0] = default_control(&descriptor->PortRangeHints[port], rate);
        }
        descriptor->connect_port(instance, port, ports[port]);
    }

    if (result == 0) {
        if (descriptor->activate != NULL) descriptor->activate(instance);
        descriptor->run(instance, FRAME_COUNT);
        for (port = 0; port < descriptor->PortCount; ++port) {
            if (!LADSPA_IS_PORT_OUTPUT(descriptor->PortDescriptors[port])) continue;
            if (LADSPA_IS_PORT_AUDIO(descriptor->PortDescriptors[port])) {
                for (frame = 0; frame < FRAME_COUNT; ++frame) {
                    if (!isfinite(ports[port][frame])) result = 1;
                }
            } else if (!isfinite(ports[port][0])) {
                result = 1;
            }
        }
        if (descriptor->deactivate != NULL) descriptor->deactivate(instance);
    }

    for (port = 0; port < descriptor->PortCount; ++port) free(ports[port]);
    free(ports);
    descriptor->cleanup(instance);
    return result;
}

static int test_module(const char *directory, const char *name,
                       unsigned int *descriptor_count) {
    char path[4096];
    void *module;
    descriptor_fn get_descriptor;
    unsigned long index;

    if (snprintf(path, sizeof(path), "%s/%s", directory, name) >= (int)sizeof(path)) {
        fprintf(stderr, "module path too long\n");
        return 1;
    }
    module = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (module == NULL) {
        fprintf(stderr, "%s: dlopen failed: %s\n", name, dlerror());
        return 1;
    }
    *(void **)(&get_descriptor) = dlsym(module, "ladspa_descriptor");
    if (get_descriptor == NULL) {
        fprintf(stderr, "%s: ladspa_descriptor missing\n", name);
        dlclose(module);
        return 1;
    }
    for (index = 0; get_descriptor(index) != NULL; ++index) {
        if (run_descriptor(get_descriptor(index)) != 0) {
            fprintf(stderr, "%s: descriptor %lu failed\n", name, index);
            dlclose(module);
            return 1;
        }
        ++*descriptor_count;
    }
    if (index == 0) {
        fprintf(stderr, "%s: no descriptors exported\n", name);
        dlclose(module);
        return 1;
    }
    dlclose(module);
    return 0;
}

int main(int argc, char **argv) {
    DIR *directory;
    struct dirent *entry;
    char *modules[EXPECTED_MODULES];
    unsigned int module_count = 0;
    unsigned int descriptor_count = 0;
    unsigned int i;

    if (argc < 2 || argc > 3) {
        fprintf(stderr, "usage: %s PLUGIN_DIR [--expect-ohos]\n", argv[0]);
        return 2;
    }
    if (argc == 3) {
        struct utsname system_info;
        if (strcmp(argv[2], "--expect-ohos") != 0 || uname(&system_info) != 0 ||
            strcmp(system_info.sysname, "HarmonyOS") != 0 ||
            (strcmp(system_info.machine, "aarch64") != 0 &&
             strcmp(system_info.machine, "arm64") != 0)) {
            fprintf(stderr, "HarmonyOS AArch64 runtime assertion failed\n");
            return 1;
        }
    }

    directory = opendir(argv[1]);
    if (directory == NULL) {
        fprintf(stderr, "cannot open %s: %s\n", argv[1], strerror(errno));
        return 1;
    }
    while ((entry = readdir(directory)) != NULL) {
        size_t length = strlen(entry->d_name);
        if (length < 4 || strcmp(entry->d_name + length - 3, ".so") != 0) continue;
        if (module_count == EXPECTED_MODULES) {
            fprintf(stderr, "more than %u modules found\n", EXPECTED_MODULES);
            closedir(directory);
            return 1;
        }
        modules[module_count] = strdup(entry->d_name);
        if (modules[module_count] == NULL) {
            closedir(directory);
            return 1;
        }
        ++module_count;
    }
    closedir(directory);
    if (module_count != EXPECTED_MODULES) {
        fprintf(stderr, "expected %u modules, found %u\n",
                EXPECTED_MODULES, module_count);
        return 1;
    }

    qsort(modules, module_count, sizeof(*modules), compare_names);
    for (i = 0; i < module_count; ++i) {
        if (test_module(argv[1], modules[i], &descriptor_count) != 0) return 1;
        free(modules[i]);
    }
    if (descriptor_count < EXPECTED_MODULES) {
        fprintf(stderr, "descriptor count %u is too small\n", descriptor_count);
        return 1;
    }
    printf("PASS: %u TAP modules, %u LADSPA descriptors, all audio runs finite\n",
           module_count, descriptor_count);
    return 0;
}
