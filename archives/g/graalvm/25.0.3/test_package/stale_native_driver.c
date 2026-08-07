#define _POSIX_C_SOURCE 200809L

#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int copy_self(const char *source_path, const char *output)
{
    char buffer[16384];
    ssize_t count;
    int source = open(source_path, O_RDONLY);
    int destination;

    if (source < 0) {
        return 2;
    }
    destination = open(output, O_WRONLY | O_CREAT | O_TRUNC, 0700);
    if (destination < 0) {
        close(source);
        return 3;
    }
    while ((count = read(source, buffer, sizeof(buffer))) > 0) {
        ssize_t written = 0;
        while (written < count) {
            ssize_t result = write(
                destination, buffer + written, (size_t)(count - written));
            if (result <= 0) {
                close(destination);
                close(source);
                return 4;
            }
            written += result;
        }
    }
    if (count < 0 || fsync(destination) != 0) {
        close(destination);
        close(source);
        return 5;
    }
    close(destination);
    close(source);
    return chmod(output, 0700) == 0 ? 0 : 6;
}

int main(int argc, char **argv)
{
    const char *output = NULL;
    int emit_output = 0;
    int emit_partial_failure = 0;
    int sleep_after_output = 0;
    int require_sanitized_environment = 0;
    int requested_exit = -1;
    int requested_signal = 0;
    const char *pid_file = NULL;
    const char *copy_source = NULL;
    const char *mutate_destination = NULL;
    int index;

    for (index = 1; index < argc; ++index) {
        if ((strcmp(argv[index], "-o") == 0 ||
             strcmp(argv[index], "--output") == 0) &&
            index + 1 < argc) {
            output = argv[++index];
        } else if (strncmp(argv[index], "--output=", 9) == 0) {
            output = argv[index] + 9;
        } else if (strncmp(argv[index], "-o=", 3) == 0) {
            output = argv[index] + 3;
        } else if (strncmp(argv[index], "-o", 2) == 0 && argv[index][2]) {
            output = argv[index] + 2;
        } else if (strcmp(argv[index], "--emit-output") == 0) {
            emit_output = 1;
        } else if (strcmp(argv[index], "--emit-partial-failure") == 0) {
            emit_partial_failure = 1;
        } else if (strcmp(argv[index], "--sleep-after-output") == 0) {
            sleep_after_output = 1;
        } else if (strcmp(argv[index], "--require-sanitized-environment") == 0) {
            require_sanitized_environment = 1;
        } else if (strcmp(argv[index], "--expect-special-arguments") == 0) {
            if (index + 2 >= argc ||
                strcmp(argv[index + 1], "value with space") != 0 ||
                argv[index + 2][0] != '\0') {
                return 13;
            }
            index += 2;
        } else if (strcmp(argv[index], "--exit-code") == 0 &&
                   index + 1 < argc) {
            char *end = NULL;
            long value = strtol(argv[++index], &end, 10);
            if (end == argv[index] || *end != '\0' || value < 1 || value > 125) {
                return 14;
            }
            requested_exit = (int)value;
        } else if (strcmp(argv[index], "--raise-signal") == 0 &&
                   index + 1 < argc) {
            const char *name = argv[++index];
            if (strcmp(name, "HUP") == 0) {
                requested_signal = SIGHUP;
            } else if (strcmp(name, "INT") == 0) {
                requested_signal = SIGINT;
            } else if (strcmp(name, "TERM") == 0) {
                requested_signal = SIGTERM;
            } else {
                return 15;
            }
        } else if (strcmp(argv[index], "--pid-file") == 0 && index + 1 < argc) {
            pid_file = argv[++index];
        } else if (strcmp(argv[index], "--copy-source") == 0 &&
                   index + 1 < argc) {
            copy_source = argv[++index];
        } else if (strcmp(argv[index], "--mutate-destination") == 0 &&
                   index + 1 < argc) {
            mutate_destination = argv[++index];
        }
    }
    if (require_sanitized_environment) {
        const char *names[] = {
            "JAVA_TOOL_OPTIONS",
            "JDK_JAVA_OPTIONS",
            "LD_LIBRARY_PATH",
            "PYTHONHOME",
            "PYTHONPATH",
            "_JAVA_OPTIONS",
        };
        size_t name_count = sizeof(names) / sizeof(names[0]);
        size_t name_index;
        for (name_index = 0; name_index < name_count; ++name_index) {
            if (getenv(names[name_index]) != NULL) {
                return 10;
            }
        }
    }
    if (requested_exit >= 0) {
        return requested_exit;
    }
    if (requested_signal != 0) {
        raise(requested_signal);
        return 16;
    }
    if (emit_partial_failure) {
        int partial = open(
            output != NULL ? output : "implicit-output",
            O_WRONLY | O_CREAT | O_TRUNC,
            0700);
        if (partial < 0) {
            return 7;
        }
        if (write(partial, "NOTELF", 6) != 6 || fsync(partial) != 0) {
            close(partial);
            return 8;
        }
        close(partial);
        return 9;
    }
    if (emit_output) {
        int result = copy_self(
            copy_source != NULL ? copy_source : argv[0],
            output != NULL ? output : "implicit-output");
        if (result != 0 || mutate_destination == NULL) {
            return result;
        }
        {
            static const char concurrent[] = "concurrent destination\n";
            int descriptor = open(
                mutate_destination, O_WRONLY | O_CREAT | O_TRUNC, 0600);
            if (descriptor < 0 ||
                write(descriptor, concurrent, sizeof(concurrent) - 1) !=
                    (ssize_t)(sizeof(concurrent) - 1) ||
                fsync(descriptor) != 0) {
                if (descriptor >= 0) {
                    close(descriptor);
                }
                return 17;
            }
            close(descriptor);
        }
        return 0;
    }
    if (sleep_after_output) {
        int result = copy_self(
            argv[0], output != NULL ? output : "implicit-output");
        if (result != 0) {
            return result;
        }
        if (pid_file != NULL) {
            int descriptor = open(
                pid_file, O_WRONLY | O_CREAT | O_TRUNC, 0600);
            char value[32];
            int length;
            if (descriptor < 0) {
                return 11;
            }
            length = snprintf(value, sizeof(value), "%ld\n", (long)getpid());
            if (length <= 0 || (size_t)length >= sizeof(value) ||
                write(descriptor, value, (size_t)length) != length ||
                fsync(descriptor) != 0) {
                close(descriptor);
                return 12;
            }
            close(descriptor);
        }
        for (;;) {
            pause();
        }
    }
    if (output != NULL) {
        (void)utimensat(AT_FDCWD, output, NULL, 0);
    }
    return 0;
}
