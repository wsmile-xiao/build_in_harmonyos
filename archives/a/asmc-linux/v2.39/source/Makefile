# AArch64 native build for Asmc host port
# Target: aarch64-unknown-linux-ohos
# Toolchain: OHOS clang 15.0.4

CC = clang
AS = clang
CFLAGS = -target aarch64-unknown-linux-ohos -O2 -g -Wall -Wextra
ASFLAGS = -target aarch64-unknown-linux-ohos -c
LDFLAGS = -target aarch64-unknown-linux-ohos -static

SRCDIR = .
BUILDDIR = build

# AArch64 assembly port files (translated from asmc x86 source)
# asmc_entry.s: entry point (setoname, cmpwarg, ReadFiles, main)
# asmc_runtime.s: memalloc.asm + ltype.asm port (MemInit/MemAlloc/LclAlloc/tstr*)
ASM_SRCS = $(SRCDIR)/asmc_entry.s $(SRCDIR)/asmc_runtime.s
ASM_OBJS = $(patsubst $(SRCDIR)/%.s,$(BUILDDIR)/%.o,$(ASM_SRCS))

# C support files (native port, musl libc)
C_SRCS = $(SRCDIR)/asmc_io.c $(SRCDIR)/asmc_globals.c $(SRCDIR)/asmc_asm.c $(SRCDIR)/asmc_elf.c
C_OBJS = $(patsubst $(SRCDIR)/%.c,$(BUILDDIR)/%.o,$(C_SRCS))

# All objects
OBJS = $(ASM_OBJS) $(C_OBJS)

TARGET = asmc_native

.PHONY: all clean rebuild list

all: $(BUILDDIR) $(TARGET)

$(BUILDDIR):
	mkdir -p $(BUILDDIR)

# Assembly files
$(BUILDDIR)/%.o: $(SRCDIR)/%.s
	$(AS) $(ASFLAGS) $< -o $@

# C files
$(BUILDDIR)/%.o: $(SRCDIR)/%.c
	$(CC) $(CFLAGS) -c $< -o $@

# Link
$(TARGET): $(OBJS)
	$(CC) $(LDFLAGS) $(OBJS) -o $@
	@echo "=== Build complete: $(TARGET) ==="
	@file $(TARGET)

# Verify provenance
verify:
	@echo "=== Verifying r168 provenance ==="
	sha256sum -c <<<"05a942edd2c6fad9abd1d0f8baecd3b735e1c49c19d814dcec6e1c682cd1423b  asmc_entry.s"
	sha256sum -c <<<"785b6db732fa2c44d118f82cab64c6b0d24c80aac32a79d5a2a2819c336d094f  asmc_entry.o"

clean:
	rm -rf $(BUILDDIR) $(TARGET)

rebuild: clean all

list:
	@echo "ASM sources: $(ASM_SRCS)"
	@echo "C sources: $(C_SRCS)"
	@echo "Objects: $(OBJS)"