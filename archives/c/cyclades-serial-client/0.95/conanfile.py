from conan import ConanFile
from conan.tools.files import get, copy, save
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout
import os, tarfile, shutil

MAKEFILE = r"""
OFLAGS=-DUSE_TERMIOS -DUSE_POSIX_NONBLOCK -DHZ=100
CCFLAGS=-O2 -Wall
SOCKFLAGS=$(OFLAGS) $(CCFLAGS) $(CFLAGS) $(CPPFLAGS)
LDLIBS=-lutil
SOCKOBJS=cyclades-ser-cli.o tsrio.o telnet.o sock.o linux-dev.o misc.o system.o measure.o
PROGS=cyclades-ser-cli
all: $(PROGS) libcsc/libcyclades-ser-cli.so
cyclades-ser-cli: $(SOCKOBJS)
	$(CC) $(LDFLAGS) -o cyclades-ser-cli $(SOCKOBJS) $(LDLIBS)
libcsc/libcyclades-ser-cli.so:
	$(MAKE) -C libcsc
%.o: %.c
	$(CC) $(SOCKFLAGS) -c $<
clean:
	$(RM) $(PROGS) *.o
	$(MAKE) -C libcsc clean
"""

LIBMAKE = r"""
CCFLAGS=-O2 -Wall -shared -fpic $(CPPFLAGS) $(CFLAGS)
SOLFLAGS=-shared -fpic -ldl $(LDFLAGS)
all: libcyclades-ser-cli.so
libcyclades-ser-cli.so: libcyclades-ser-cli.c
	$(CC) -c $(CCFLAGS) libcyclades-ser-cli.c -o libcyclades-ser-cli.o
	$(CC) libcyclades-ser-cli.o $(SOLFLAGS) -o libcyclades-ser-cli.so
clean:
	$(RM) libcyclades-ser-cli.so libcyclades-ser-cli.o
"""

class CycladesSerialClientConan(ConanFile):
    name = "cyclades-serial-client"
    version = "0.95"
    description = "Serial Port Interface for Cyclades Terminal Servers"
    license = "GPL-2.0-only"
    homepage = "https://salsa.debian.org/debian/cyclades-serial-client"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            with tarfile.open(local) as tf:
                tf.extractall(self.source_folder)
            entries = [e for e in os.listdir(self.source_folder) if e not in (".", "..")]
            if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                inner = os.path.join(self.source_folder, entries[0])
                for n in os.listdir(inner):
                    os.rename(os.path.join(inner, n), os.path.join(self.source_folder, n))
                shutil.rmtree(inner)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        save(self, os.path.join(self.source_folder, "Makefile"), MAKEFILE)
        save(self, os.path.join(self.source_folder, "libcsc", "Makefile"), LIBMAKE)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        self.run("make -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "cyclades-ser-cli", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cyclades-serial-client", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "libcyclades-ser-cli.so", src=os.path.join(self.source_folder, "libcsc"), dst=os.path.join(self.package_folder, "lib"))
        copy(self, "cyclades-devices", src=self.source_folder, dst=os.path.join(self.package_folder, "etc"))
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"), dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
