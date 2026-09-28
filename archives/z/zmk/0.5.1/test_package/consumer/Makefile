# Minimal consumer project for the installed zmk Make library.
ZMK.Path ?= /usr/local/include
-include config.zmk.mk
include $(ZMK.Path)/z.mk

Project.Name = hello
Project.Version = 1.0
hello.Sources = hello.c

$(eval $(call ZMK.Expand,Program,hello))
