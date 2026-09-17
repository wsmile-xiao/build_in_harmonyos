#!/usr/bin/env python3
"""Conan recipe — libaudit 2.7.4 (Linux Audit System userspace libraries).

libaudit is the client library of the Linux Audit System: it talks to the
kernel audit subsystem over a NETLINK_AUDIT socket (audit_open/audit_send/
audit_get_reply) and provides rule-construction helpers
(audit_rule_fieldpair_data, audit_rule_syscallbyname_data, ...) plus the
syscall/machine lookup tables.  This package name ("libaudit", not "audit")
is the library-only packaging of the linux-audit/audit-userspace monorepo —
same source tree as the already-archived audit/4.1.2, but the deliverable
here is the library + auparse for consumers that link against it.

Upstream: https://github.com/linux-audit/audit-userspace (tag audit-2.7.4 —
note the tag has NO "v" prefix for the 2.7.x series).

Build system: autotools (the GitHub tag archive ships configure.ac +
Makefile.am but no generated `configure`, so the recipe bootstraps with
`autoreconf -fi` under a VirtualBuildEnv that pulls automake/libtool in as
tool_requires — same approach as libuninameslist/0.3.20130501).

OHOS adaptations (17 patches; guards use libc-feature checks
`#if !defined(__GLIBC__)` / plain `#ifndef` where a POSIX equivalent
exists — no `#ifdef __OHOS__` platform macros, per R8; see patches/ and
notes.md):
  - R8 note: after AI review rounds, patches use libc-feature
    guards (#if !defined(__GLIBC__)) or plain #ifndef/unconditional
    POSIX replacements — no #ifdef __OHOS__ platform macros remain
    in patches. The only "no POSIX equivalent" item left is the
    pthread_cancel -> pthread_kill(0) macro substitute (musl has no
    cancellation API at all), which matches the merged audit/4.1.2
    precedent (its patches/0005).
  - linux/socket.h uapi vs sys/socket.h sockaddr_storage redefinition
    (E-derived from audit/4.1.2 experience): guard defined before either
    header is included, plus a __kernel_sa_family_t typedef, in
    lib/libaudit.h and every TU that includes <linux/net.h> first.
  - AUDIT_FILTER_EXCLUDE macro redefinition vs the OHOS kernel uapi
    linux/audit.h (upstream assumed pre-2.6.30 kernels).
  - rawmemchr / strndupa / pthread_cancel / PATH_MAX / fd_set+sys/select.h:
    glibc-only APIs and implicit includes that OHOS musl-bionic libc does
    not provide. strndupa is a MACRO (not static inline) on purpose: clang's
    inliner emits llvm.lifetime markers that invalidate the alloca'd buffer
    of an inlined function right after the call — observed as corrupted
    tokens in auparse_test (root-caused with a standalone reproducer).
  - ausearch-common.h tentative definition `slist *event_node_list;`
    becomes a duplicate symbol under lld's default -fno-common.
  - audisp/remote queue.c posix_fallocate: POSIX says the RETURN VALUE is
    the error number and errno is not guaranteed (glibc just happens to set
    it).  OHOS HMDFS does not implement allocation: posix_fallocate returns
    EACCES with errno untouched, so the return code is inspected and the
    code falls back to ftruncate (same file-size guarantee).
  - test-queue.c /tmp template: OHOS mounts /tmp read-only (E002); the
    template honours $TMPDIR with /data/local/tmp fallback.
  - audit netlink runtime shape (W0 finding, declared in PR body):
    socket(PF_NETLINK, SOCK_RAW, NETLINK_AUDIT) exists as a constant and the
    syscall path is wired, but the OHOS kernel/SELinux policy denies it for
    the app sandbox (EACCES) — same errno surface as Linux without audit
    support.  audit_open() therefore fails gracefully exactly as designed;
    the pure-library lookups (audit_detect_machine, audit_name_to_syscall,
    ausearch parsing) are fully functional and covered by tests.

Build/link strategy (static deliverable):
  The default (shared-enabled) autotools build produces libaudit.so /
  libauparse.so plus the sbin tools linked against them; the static-only
  build (`--disable-shared`) cannot link the auditd binary because
  src/auditd-config.c and auparse/auditd-config.c both define
  clear_config/free_config (upstream resolves that collision via ELF
  visibility, which static archives do not have).  The recipe therefore
  builds the default configuration and packages ONLY the static archives
  (.a) plus headers and tools — R26: the system-same-name .so never lands
  in the package, so nothing can shadow /lib or /lib64.

Rules compliance:
  R1:  Minimal configure args (only the platform-neutral feature switches
       needed to drop unbuilt bindings: --without-python/--without-python3/
       --without-golang/--without-libcap-ng + --disable-zos-remote/
       --disable-listener; prefix handled by AutotoolsToolchain).
  R26: System same-name libraries (libaudit, libauparse): .so removed at
       package() time — the deliverable is static-only.
  R32: settings.os validated with in ("Linux", "OHOS").
  R33: No bare ${CC}/${CFLAGS} — everything goes through AutotoolsToolchain
       and VirtualBuildEnv.
  R38: The recipe builds CLI tools (auditctl/auditd/aureport/ausearch/
       ausyscall/...) into sbin/; commands.json is declared at the software
       level (archives/l/libaudit/commands.json).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


def _drop_umask_077(path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077` from the generated configure so config.status can
    create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class LibauditConan(ConanFile):
    name = "libaudit"
    version = "2.7.4"
    description = (
        "Linux Audit System client library (libaudit) and audit-log "
        "parsing library (libauparse), from audit-userspace 2.7.4"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/linux-audit/audit-userspace"
    url = ""  # CI fills this

    # R26: audit-userspace produces the system same-name libraries libaudit
    # and libauparse; the deliverable is static-only (the .so produced by
    # the default build is removed at package() time).
    package_type = "static-library"
    languages = "C"
    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # pure C project: drop C++ settings (no libc++ ABI split needed)
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        # R32: settings.os must be checked with in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libaudit is only supported on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # R3: patches declared in conandata.yml (17 portability patches)
        export_conandata_patches(self)

    def build_requirements(self):
        # The tag archive ships configure.ac/Makefile.am but no generated
        # `configure`: bootstrap with `autoreconf -fi`, which execs the whole
        # autotools closure by bare name. automake + libtool come in as
        # tool_requires so the closure is complete on a clean CI worker
        # (autoconf itself is on the worker PATH via the SDK — same split
        # as libuninameslist/0.3.20130501).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # VirtualBuildEnv: inject profile [buildenv] PATH + tool_requires
        # (automake/libtool) bindirs so the autotools closure resolves.
        build_env = VirtualBuildEnv(self)
        build_env.generate()
        tc = AutotoolsToolchain(self)
        # E007/E514: pin both triplets so the shipped config.guess probe
        # never runs and the (old) config.sub is irrelevant.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # Feature switches (R1-minimal: only what is needed to build cleanly
        # on a worker without python/go headers):
        tc.configure_args.append("--without-python")
        tc.configure_args.append("--without-python3")
        tc.configure_args.append("--without-golang")
        # libcap-ng is optional (W0: present in registry but the auditctl
        # capng codepaths are Linux-capability specific; keep the library
        # dependency surface empty for this port).
        tc.configure_args.append("--without-libcap-ng")
        # zos-remote plugin: mainframe-only, needs libwrap; the listener
        # adds auditd network attack surface — both off for the PC port.
        tc.configure_args.append("--disable-zos-remote")
        tc.configure_args.append("--disable-listener")
        # Build with shared libs ENABLED (overriding the static-only
        # default AutotoolsToolchain derives from package_type): the sbin
        # tools cannot be linked against the static archives because
        # src/auditd-config.c and auparse/auditd-config.c define the same
        # hidden symbols (clear_config/free_config) and ELF visibility
        # does not exist for static archive members. The .so never lands
        # in the package (removed in package(), R26).
        tc.configure_args.append("--enable-shared")
        # NOTE: no __OHOS__ define injection — the OHOS clang toolchain
        # predefines __OHOS__ itself, and the patches guard on it.
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        build_env = VirtualBuildEnv(self).vars()
        with build_env.apply():
            # Tag archive ships no `configure`: generate it in-place.
            self.run("autoreconf -f -i", cwd=self.source_folder)
        # E114: drop umask 077 from the generated configure (HMDFS setgid)
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        autotools = Autotools(self)
        autotools.configure()
        # E074: HMDFS jobserver fifo EPERM — serial make.
        # NOTE: the default (shared-enabled) build is intentional — see the
        # module docstring: --disable-shared cannot link auditd because
        # src/auditd-config.c and auparse/auditd-config.c define the same
        # hidden symbols and static archives have no ELF visibility.
        autotools.make(args=["-j1"])
        # Upstream test suite runs from the build tree (check_PROGRAMS are
        # already built by `make`); L1c evidence for the CI gate.
        autotools.make(args=["-j1", "check"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # R26: the deliverable is the static archive — the system-same-name
        # shared objects must not land in the package (they would be a
        # candidate for shadowing /lib, /lib64 when installed).
        for pattern in ("*.so", "*.so.*", "*.la", "*.dylib", "*.dll"):
            rm(self, pattern, os.path.join(self.package_folder, "lib"),
               recursive=True)
        # libtool convenience symlinks are already gone with the .so; keep
        # the tree tidy of any remaining oddities.
        for leftover in glob.glob(os.path.join(self.package_folder,
                                               "lib", "*.so*")):
            if os.path.islink(leftover) or os.path.isfile(leftover):
                os.remove(leftover)

    def package_info(self):
        # Components so consumers can link the two libraries explicitly
        # (test_package links both audit and auparse symbols; a single
        # aggregate target would rely on an implicit contract).
        self.cpp_info.set_property("cmake_file_name", "libaudit")
        self.cpp_info.components["audit"].libs = ["audit"]
        self.cpp_info.components["audit"].set_property(
            "cmake_target_name", "libaudit::audit")
        self.cpp_info.components["audit"].set_property(
            "pkg_config_name", "audit")
        self.cpp_info.components["auparse"].libs = ["auparse"]
        self.cpp_info.components["auparse"].set_property(
            "cmake_target_name", "libaudit::auparse")
        self.cpp_info.components["auparse"].set_property(
            "pkg_config_name", "auparse")
        self.cpp_info.components["auparse"].requires = ["audit"]
        self.cpp_info.includedirs = ["include"]
