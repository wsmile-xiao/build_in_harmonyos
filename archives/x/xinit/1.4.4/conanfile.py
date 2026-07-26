#!/usr/bin/env python3
"""Conan recipe - xinit 1.4.4."""
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XinitConan(ConanFile):
    name = "xinit"
    version = "1.4.4"
    description = "X.Org initialisation program"
    license = "MIT-open-group"
    homepage = "https://www.x.org/"
    url = "https://www.x.org/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        x11_prefix = os.path.join(self.source_folder, "res", "x11")
        include_flags = f"-I{x11_prefix}/include"
        lib_flags = f"{x11_prefix}/lib/libX11.a"
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            f"--x-includes={x11_prefix}/include",
            f"--x-libraries={x11_prefix}/lib",
            f"CPPFLAGS={include_flags}",
            f"CFLAGS={include_flags} -fPIC -O2",
            f"LDFLAGS=-L{x11_prefix}/lib",
            f"XINIT_CFLAGS={include_flags}",
            f"XINIT_LIBS={lib_flags}",
        ])
        tc.extra_cflags.extend(include_flags.split())
        tc.extra_ldflags.append(f"-L{x11_prefix}/lib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._build_x11_compat()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        binary = os.path.join(self.package_folder, "bin", "xinit")
        if os.path.exists(binary):
            self._sign_binary(binary)

    def _sign_binary(self, path):
        os.chmod(path, 0o755)
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if str(self.settings.os) != "OHOS" or not (os.path.exists(sign_tool) and os.path.exists(objcopy)):
            return
        tmp_signed = path + ".signed"
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp_signed, "-selfSign", "1"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def _compiler_path(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return compilers.get("c") or "cc"

    def _build_x11_compat(self):
        root = os.path.join(self.source_folder, "res", "x11")
        include_dir = os.path.join(root, "include", "X11")
        lib_dir = os.path.join(root, "lib")
        os.makedirs(include_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)

        headers = {
            "Xfuncproto.h": r"""
#ifndef X11_XFUNCPROTO_H
#define X11_XFUNCPROTO_H
#if defined(__GNUC__) || defined(__clang__)
#define _X_ATTRIBUTE_PRINTF(x, y) __attribute__((format(printf, x, y)))
#define _X_NORETURN __attribute__((noreturn))
#define _X_UNUSED __attribute__((unused))
#else
#define _X_ATTRIBUTE_PRINTF(x, y)
#define _X_NORETURN
#define _X_UNUSED
#endif
#endif
""",
            "Xos.h": r"""
#ifndef X11_XOS_H
#define X11_XOS_H
#include <string.h>
#include <strings.h>
#include <unistd.h>
#endif
""",
            "Xatom.h": r"""
#ifndef X11_XATOM_H
#define X11_XATOM_H
#define XA_PRIMARY ((Atom)1)
#define XA_SECONDARY ((Atom)2)
#define XA_ARC ((Atom)3)
#define XA_ATOM ((Atom)4)
#define XA_BITMAP ((Atom)5)
#define XA_CARDINAL ((Atom)6)
#define XA_INTEGER ((Atom)19)
#define XA_WINDOW ((Atom)33)
#endif
""",
            "Xlib.h": r"""
#ifndef X11_XLIB_H
#define X11_XLIB_H
#include <stddef.h>
#include <stdint.h>
#include "Xfuncproto.h"
typedef struct _XDisplay Display;
typedef unsigned long XID;
typedef XID Window;
typedef unsigned long Atom;
typedef int Bool;
#ifndef True
#define True 1
#endif
#ifndef False
#define False 0
#endif
#ifndef None
#define None 0L
#endif
#ifndef AnyPropertyType
#define AnyPropertyType 0L
#endif
#define DefaultRootWindow(dpy) ((Window)0)
Display *XOpenDisplay(const char *display_name);
int XCloseDisplay(Display *display);
Atom XInternAtom(Display *display, const char *atom_name, Bool only_if_exists);
int XGetWindowProperty(Display *display, Window window, Atom property, long long_offset,
                       long long_length, Bool delete_property, Atom req_type,
                       Atom *actual_type_return, int *actual_format_return,
                       unsigned long *nitems_return, unsigned long *bytes_after_return,
                       unsigned char **prop_return);
int XFree(void *data);
int (*XSetIOErrorHandler(int (*handler)(Display *)))(Display *);
#endif
""",
        }
        for name, content in headers.items():
            with open(os.path.join(include_dir, name), "w", encoding="utf-8") as handle:
                handle.write(content.strip() + "\n")

        stub_c = os.path.join(root, "x11_stub.c")
        with open(stub_c, "w", encoding="utf-8") as handle:
            handle.write(r"""
#include <stdlib.h>
#include <X11/Xlib.h>

struct _XDisplay { int unused; };

Display *XOpenDisplay(const char *display_name)
{
    (void)display_name;
    return NULL;
}

int XCloseDisplay(Display *display)
{
    (void)display;
    return 0;
}

Atom XInternAtom(Display *display, const char *atom_name, Bool only_if_exists)
{
    (void)display;
    (void)atom_name;
    (void)only_if_exists;
    return None;
}

int XGetWindowProperty(Display *display, Window window, Atom property, long long_offset,
                       long long_length, Bool delete_property, Atom req_type,
                       Atom *actual_type_return, int *actual_format_return,
                       unsigned long *nitems_return, unsigned long *bytes_after_return,
                       unsigned char **prop_return)
{
    (void)display;
    (void)window;
    (void)property;
    (void)long_offset;
    (void)long_length;
    (void)delete_property;
    (void)req_type;
    if (actual_type_return != NULL) {
        *actual_type_return = None;
    }
    if (actual_format_return != NULL) {
        *actual_format_return = 0;
    }
    if (nitems_return != NULL) {
        *nitems_return = 0;
    }
    if (bytes_after_return != NULL) {
        *bytes_after_return = 0;
    }
    if (prop_return != NULL) {
        *prop_return = NULL;
    }
    return 1;
}

int XFree(void *data)
{
    free(data);
    return 0;
}

int (*XSetIOErrorHandler(int (*handler)(Display *)))(Display *)
{
    static int (*previous)(Display *) = NULL;
    int (*old)(Display *) = previous;
    previous = handler;
    return old;
}
""".lstrip())
        obj = os.path.join(root, "x11_stub.o")
        lib = os.path.join(lib_dir, "libX11.a")
        cc = self._compiler_path()
        ar = os.environ.get("AR", "llvm-ar")
        self.run(
            f"{shlex.quote(cc)} -fPIC -O2 -I{shlex.quote(os.path.join(root, 'include'))} "
            f"-c {shlex.quote(stub_c)} -o {shlex.quote(obj)}",
            env="conanbuild",
            cwd=self.source_folder,
        )
        self.run(
            f"{shlex.quote(ar)} rcs {shlex.quote(lib)} {shlex.quote(obj)}",
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
