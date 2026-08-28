#ifndef MODULE_PROBE_H
#define MODULE_PROBE_H

int probe_executable_path(char *path, int capacity, int *dirname_length);
int probe_module_path(char *path, int capacity, int *dirname_length);

#endif
