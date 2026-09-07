/* Copyright (c) 2010: Michal Kottman */

#define BUILDING_ACPICA

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/version.h>
#include <linux/proc_fs.h>
#include <linux/slab.h>
#include <linux/mutex.h>
#include <linux/uaccess.h>
#include <stdarg.h>
#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 14, 0)
#include <asm/uaccess.h>
#endif
#if LINUX_VERSION_CODE >= KERNEL_VERSION(3, 17, 0)
#include <linux/acpi.h>
#else
#include <acpi/acpi.h>
#endif

MODULE_LICENSE("GPL");

/* Uncomment the following line to enable debug messages */
/*
#define DEBUG
*/

#define BUFFER_SIZE 4096
#define INPUT_BUFFER_SIZE (2 * BUFFER_SIZE)
#define MAX_ACPI_ARGS 16

#if LINUX_VERSION_CODE >= KERNEL_VERSION(3, 10, 0)
#define HAVE_PROC_CREATE
#endif

extern struct proc_dir_entry *acpi_root_dir;

static char input_buffer[INPUT_BUFFER_SIZE];
static char result_buffer[BUFFER_SIZE];
static char not_called_message[11] = "not called";

static u8 temporary_buffer[BUFFER_SIZE];
static DEFINE_MUTEX(acpi_call_mutex);

static size_t get_avail_bytes(void) {
    return BUFFER_SIZE - strlen(result_buffer);
}
static char *get_buffer_end(void) {
    return result_buffer + strlen(result_buffer);
}

/** Appends formatted output to the result buffer without overflowing it
@param fmt   printf-style format string
@returns     the number of bytes appended, or -1 on error/truncation
*/
static int append_result(const char *fmt, ...) {
    va_list args;
    size_t avail = get_avail_bytes();
    int written;

    if (avail == 0)
        return -1;

    va_start(args, fmt);
    written = vsnprintf(get_buffer_end(), avail, fmt, args);
    va_end(args);

    if (written < 0 || (size_t) written >= avail)
        return -1;
    return written;
}

/** Appends the contents of an acpi_object to the result buffer
@param result   An acpi object holding result data
@returns        0 if the result could fully be saved, a higher value otherwise
*/
static int acpi_result_to_string(union acpi_object *result) {
    if (result->type == ACPI_TYPE_INTEGER) {
        if (append_result("0x%llx",
                          (unsigned long long) result->integer.value) < 0)
            return 1;
    } else if (result->type == ACPI_TYPE_STRING) {
        size_t string_length = min_t(size_t, result->string.length,
                                     BUFFER_SIZE);
        if (append_result("\"%.*s\"", (int) string_length,
                          result->string.pointer) < 0)
            return 1;
    } else if (result->type == ACPI_TYPE_BUFFER) {
        size_t i;

        if (append_result("{") < 0)
            return 1;
        for (i = 0; i < result->buffer.length; i++) {
            if (append_result(i == 0 ? "0x%02x" : ", 0x%02x",
                              result->buffer.pointer[i]) < 0)
                return 1;
        }

        if (append_result("}") < 0)
            return 1;
    } else if (result->type == ACPI_TYPE_PACKAGE) {
        size_t i;
        if (append_result("[") < 0)
            return 1;
        for (i = 0; i < result->package.count; i++) {
            if (i > 0 && append_result(", ") < 0)
                return 1;

            // abort if there is no more space available
            if (acpi_result_to_string(&result->package.elements[i]))
                return 1;
        }
        if (append_result("]") < 0)
            return 1;
    } else {
        if (append_result("Object type 0x%x\n", result->type) < 0)
            return 1;
    }

    return 0;
}

/**
@param method   The full name of ACPI method to call
@param argc     The number of parameters
@param argv     A pre-allocated array of arguments of type acpi_object
*/
static void do_acpi_call(const char * method, int argc, union acpi_object *argv)
{
    acpi_status status;
    acpi_handle handle;
    struct acpi_object_list arg;
    struct acpi_buffer buffer = { ACPI_ALLOCATE_BUFFER, NULL };

#ifdef DEBUG
    printk(KERN_INFO "acpi_call: Calling %s\n", method);
#endif

    // get the handle of the method, must be a fully qualified path
    status = acpi_get_handle(NULL, (acpi_string) method, &handle);

    if (ACPI_FAILURE(status))
    {
        snprintf(result_buffer, BUFFER_SIZE, "Error: %s", acpi_format_exception(status));
        printk(KERN_ERR "acpi_call: Cannot get handle: %s\n", result_buffer);
        return;
    }

    // prepare parameters
    arg.count = argc;
    arg.pointer = argv;

    // call the method
    status = acpi_evaluate_object(handle, NULL, &arg, &buffer);
    if (ACPI_FAILURE(status))
    {
        snprintf(result_buffer, BUFFER_SIZE, "Error: %s", acpi_format_exception(status));
        printk(KERN_ERR "acpi_call: Method call failed: %s\n", result_buffer);
        return;
    }

    // A successful void method has no result object. Otherwise, report a
    // truncation error instead of silently returning a partial result.
    *result_buffer = '\0';
    if (!buffer.pointer) {
        if (append_result("ok") < 0)
            snprintf(result_buffer, BUFFER_SIZE, "Error: result too long");
    } else if (acpi_result_to_string(buffer.pointer)) {
        snprintf(result_buffer, BUFFER_SIZE, "Error: result too long");
    }
    kfree(buffer.pointer);

#ifdef DEBUG
    printk(KERN_INFO "acpi_call: Call successful: %s\n", result_buffer);
#endif
}

/** Decodes 2 hex characters to an u8 int
*/
static u8 decodeHex(char *hex) {
    char buf[3] = { hex[0], hex[1], 0};
    return (u8) simple_strtoul(buf, NULL, 16);
}

/** Parses method name and arguments
@param input Input string to be parsed. Modified in the process.
@param nargs Set to number of arguments parsed (output)
@param args
*/
static char *parse_acpi_args(char *input, int *nargs, union acpi_object **args)
{
    char *s = input;
    int i;

    *nargs = 0;
    *args = NULL;

    // the method name is separated from the arguments by a space
    while (*s && *s != ' ')
        s++;
    // if no space is found, return 0 arguments
    if (*s == 0)
        return input;

    *s = 0; // change the first space to nul
    ++s;

    *args = (union acpi_object *) kzalloc(MAX_ACPI_ARGS * sizeof(union acpi_object), GFP_KERNEL);
    if (!*args) {
        printk(KERN_ERR "acpi_call: unable to allocate buffer\n");
        return NULL;
    }

    while (*s) {
        if (*s == ' ') {
            ++ s;
        } else {
            union acpi_object *arg;
            if (*nargs >= MAX_ACPI_ARGS) {
                printk(KERN_ERR "acpi_call: too many arguments\n");
                goto err;
            }
            arg = (*args) + *nargs;
            ++ *nargs;
            if (*s == '"') {
                // decode string
                arg->type = ACPI_TYPE_STRING;
                arg->string.pointer = ++s;
                arg->string.length = 0;
                while (*s && *s++ != '"')
                    arg->string.length ++;
                // skip the last "
                if (*s == '"')
                    ++s;
            } else if (*s == 'b') {
                // decode buffer - bXXXX
                char *p = ++s;
                int len = 0, i;
                u8 *buf = NULL;

                while (*p && *p!=' ')
                    p++;

                len = p - s;
                if (len % 2 == 1) {
                    printk(KERN_ERR "acpi_call: buffer arg%d is not multiple of 8 bits\n", *nargs);
                    --*nargs;
                    goto err;
                }
                len /= 2;

                buf = (u8*) kmalloc(len, GFP_KERNEL);
                if (!buf) {
                    printk(KERN_ERR "acpi_call: unable to allocate buffer\n");
                    --*nargs;
                    goto err;
                }
                for (i=0; i<len; i++) {
                    buf[i] = decodeHex(s + i*2);
                }
                s = p;

                arg->type = ACPI_TYPE_BUFFER;
                arg->buffer.pointer = buf;
                arg->buffer.length = len;
            } else if (*s == '{') {
                // decode buffer - { b1, b2 ...}
                u8 *buf = temporary_buffer;
                arg->type = ACPI_TYPE_BUFFER;
                arg->buffer.pointer = buf;
                arg->buffer.length = 0;
                while (*s && *s++ != '}') {
                    if (buf >= temporary_buffer + sizeof(temporary_buffer)) {
                        printk(KERN_ERR "acpi_call: buffer arg%d is truncated because the buffer is full\n", *nargs);
                        // clear remaining arguments
                        while (*s && *s != '}')
                            ++s;
                        break;
                    }
                    else if (*s >= '0' && *s <= '9') {
                        // decode integer into buffer
                        arg->buffer.length ++;
                        if (s[0] == '0' && s[1] == 'x')
                            *buf++ = simple_strtol(s+2, 0, 16);
                        else
                            *buf++ = simple_strtol(s, 0, 10);
                    }
                    // skip until space or comma or '}'
                    while (*s && *s != ' ' && *s != ',' && *s != '}')
                        ++s;
                }
                // store the result in new allocated buffer
                buf = (u8*) kmalloc(arg->buffer.length, GFP_KERNEL);
                if (!buf) {
                    printk(KERN_ERR "acpi_call: unable to allocate buffer\n");
                    --*nargs;
                    goto err;
                }
                memcpy(buf, temporary_buffer, arg->buffer.length);
                arg->buffer.pointer = buf;
            } else {
                // decode integer, N or 0xN
                arg->type = ACPI_TYPE_INTEGER;
                if (s[0] == '0' && s[1] == 'x') {
                    arg->integer.value = simple_strtol(s+2, 0, 16);
                } else {
                    arg->integer.value = simple_strtol(s, 0, 10);
                }
                while (*s && *s != ' ') {
                    ++s;
                }
            }
        }
    }

    return input;

err:
    for (i=0; i<*nargs; i++)
        if ((*args)[i].type == ACPI_TYPE_BUFFER && (*args)[i].buffer.pointer)
            kfree((*args)[i].buffer.pointer);
    kfree(*args);
    *args = NULL;
    return NULL;
}

/** procfs write callback. Called when writing into /proc/acpi/call.
*/
#ifdef HAVE_PROC_CREATE
static ssize_t acpi_proc_write( struct file *filp, const char __user *buff,
    size_t len, loff_t *data )
#else
static int acpi_proc_write( struct file *filp, const char __user *buff,
    unsigned long len, void *data )
#endif
{
    union acpi_object *args;
    int nargs, i;
    char *method;
#ifdef HAVE_PROC_CREATE
    ssize_t ret;
#else
    int ret;
#endif

    mutex_lock(&acpi_call_mutex);
    memset(input_buffer, 0, INPUT_BUFFER_SIZE);
    if (len > sizeof(input_buffer) - 1) {
#ifdef HAVE_PROC_CREATE
        printk(KERN_ERR "acpi_call: Input too long! (%zu)\n", len);
#else
        printk(KERN_ERR "acpi_call: Input too long! (%lu)\n", len);
#endif
        ret = -ENOSPC;
        goto out;
    }

    if (copy_from_user( input_buffer, buff, len )) {
        ret = -EFAULT;
        goto out;
    }
    input_buffer[len] = '\0';
    if (len > 0 && input_buffer[len-1] == '\n')
        input_buffer[len-1] = '\0';

    method = parse_acpi_args(input_buffer, &nargs, &args);
    if (method) {
        do_acpi_call(method, nargs, args);
        if (args) {
            for (i=0; i<nargs; i++)
                if (args[i].type == ACPI_TYPE_BUFFER)
                    kfree(args[i].buffer.pointer);
        }
    }
    if (args)
        kfree(args);

    ret = len;
out:
    mutex_unlock(&acpi_call_mutex);
    return ret;
}

/** procfs 'call' read callback. Called when reading the content of /proc/acpi/call.
Returns the last call status:
- "not called" when no call was previously issued
- "failed" if the call failed
- "ok" if the call succeeded
*/
#ifdef HAVE_PROC_CREATE
static ssize_t acpi_proc_read( struct file *filp, char __user *buff,
            size_t count, loff_t *off )
{
    ssize_t ret;
    int len;

    mutex_lock(&acpi_call_mutex);
    len = strlen(result_buffer);
    if(len == 0) {
        ret = simple_read_from_buffer(buff, count, off, not_called_message, strlen(not_called_message) + 1);
    } else if(len + 1 > count) {
        // user buffer is too small
        ret = 0;
    } else if(*off == len + 1) {
        // we're done
        ret = 0;
        result_buffer[0] = '\0';
    } else {
        // output the current result buffer
        ret = simple_read_from_buffer(buff, count, off, result_buffer, len + 1);
        *off = ret;
    }
    mutex_unlock(&acpi_call_mutex);

    return ret;
}

#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 6, 0)
static struct proc_ops proc_acpi_operations = {
	.proc_read = acpi_proc_read,
	.proc_write = acpi_proc_write,
#if LINUX_VERSION_CODE >= KERNEL_VERSION(5, 13, 0)
	.proc_lseek = default_llseek,
#endif
};
#else
static struct file_operations proc_acpi_operations = {
        .owner    = THIS_MODULE,
        .read     = acpi_proc_read,
        .write    = acpi_proc_write,
};
#endif

#else
static int acpi_proc_read(char *page, char **start, off_t off,
    int count, int *eof, void *data)
{
    int len = 0;
    int ret;

    mutex_lock(&acpi_call_mutex);
    if (off > 0) {
        *eof = 1;
        ret = 0;
        goto out;
    }

    // output the current result buffer
    len = strlen(result_buffer);
    memcpy(page, result_buffer, len + 1);

    // initialize the result buffer for later
    strcpy(result_buffer, "not called");

    ret = len;
out:
    mutex_unlock(&acpi_call_mutex);
    return ret;
}
#endif

/** module initialization function */
static int __init init_acpi_call(void)
{
#ifdef HAVE_PROC_CREATE
    struct proc_dir_entry *acpi_entry = proc_create("call",
                                                    0660,
                                                    acpi_root_dir,
                                                    &proc_acpi_operations);
#else
    struct proc_dir_entry *acpi_entry = create_proc_entry("call", 0660, acpi_root_dir);
#endif

    strcpy(result_buffer, "not called");

    if (acpi_entry == NULL) {
      printk(KERN_ERR "acpi_call: Couldn't create proc entry\n");
      return -ENOMEM;
    }

#ifndef HAVE_PROC_CREATE
    acpi_entry->write_proc = acpi_proc_write;
    acpi_entry->read_proc = acpi_proc_read;
#endif

#ifdef DEBUG
    printk(KERN_INFO "acpi_call: Module loaded successfully\n");
#endif

    return 0;
}

static void __exit unload_acpi_call(void)
{
    remove_proc_entry("call", acpi_root_dir);

#ifdef DEBUG
    printk(KERN_INFO "acpi_call: Module unloaded successfully\n");
#endif
}

module_init(init_acpi_call);
module_exit(unload_acpi_call);
