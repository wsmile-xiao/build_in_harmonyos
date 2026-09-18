# Portable Makefile for the OpenV2G EXI and V2GTP library.
# The upstream archive ships Eclipse project makefiles for an executable
# example. This target builds the reusable C implementation as a library.

NAME := openv2g
PREFIX ?= /usr/local
DESTDIR ?=
CC ?= clang
AR ?= llvm-ar
RANLIB ?= llvm-ranlib
CPPFLAGS ?=
CFLAGS ?= -O2 -Wall -Wextra -fPIC
LDFLAGS ?=
SHARED ?= 0

SOURCE_DIRS := src/codec src/transport src/appHandshake src/din src/iso1 src/iso2 src/xmldsig
SOURCES := $(foreach dir,$(SOURCE_DIRS),$(wildcard $(dir)/*.c))
OBJECTS := $(patsubst %.c,build/%.o,$(SOURCES))
HEADERS := $(foreach dir,$(SOURCE_DIRS),$(wildcard $(dir)/*.h))
INCLUDES := $(foreach dir,$(SOURCE_DIRS),-I$(dir))

ifeq ($(SHARED),1)
LIBRARY := lib$(NAME).so
else
LIBRARY := lib$(NAME).a
endif

.PHONY: all install clean

all: $(LIBRARY)

$(LIBRARY): $(OBJECTS)
ifeq ($(SHARED),1)
	$(CC) $(LDFLAGS) -shared -o $@ $^
else
	$(AR) rcs $@ $^
	$(RANLIB) $@
endif

build/%.o: %.c
	@mkdir -p $(dir $@)
	$(CC) $(CPPFLAGS) $(INCLUDES) $(CFLAGS) -MMD -MP -c $< -o $@

install: $(LIBRARY)
	@mkdir -p "$(DESTDIR)$(PREFIX)/lib" "$(DESTDIR)$(PREFIX)/include"
	@cp "$(LIBRARY)" "$(DESTDIR)$(PREFIX)/lib/"
	@for header in $(HEADERS); do \
		cp "$$header" "$(DESTDIR)$(PREFIX)/include/$$(basename "$$header")"; \
	done

clean:
	rm -rf build "$(LIBRARY)"

-include $(OBJECTS:.o=.d)
