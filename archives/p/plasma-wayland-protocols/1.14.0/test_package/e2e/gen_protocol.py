#!/usr/bin/env python3
"""Build-time protocol generator for the plasma-wayland-protocols end-to-end test.

plasma-wayland-protocols delivers protocol *descriptions*: a consumer turns them
into code with wayland-scanner and then speaks the protocol.  This generator does
that same job for the protocol the end-to-end flow exercises -- it reads
``keystate.xml`` out of the installed package and emits the ``wl_interface``
table, the enums, and the client/server call wrappers that ``plasma_e2e.c`` then
uses for a real client<->server exchange over libwayland.

Why the test carries its own generator: on OHOS the ``wayland-scanner`` binary of
the wayland package is an unexecutable ELF (the loader rejects it; PR #13500 is
the fix), so the scanner cannot be invoked from a test build yet.  Everything
else in the flow is the real thing -- the protocol description comes from the
installed package, and the generated tables drive a real libwayland client and
server over a real AF_UNIX socket.

Faithfulness: names are emitted exactly as declared in the XML (wayland-scanner
does not change the case of request/event names), and the message signature
strings use the same convention, i.e. one letter per argument with a trailing
digit when the message is versioned ("4" for destroy, "uu" for stateChanged).

Being strict is the point: anything the generator cannot translate exactly is a
hard error, so the emitted tables can never silently disagree with the XML.

usage: gen_protocol.py <keystate.xml> <output-dir>
"""
import hashlib
import os
import sys
import xml.etree.ElementTree as ET

# The interface the flow exercises; keystate.xml declares exactly this one.
IFACE_NAME = "org_kde_kwin_keystate"
INTERFACE_VERSION = 4

# Argument types translated faithfully.  keystate.xml only uses uint; a protocol
# using anything else must extend this table rather than have the generator guess.
SCALAR_TYPES = {"uint": "uint32_t", "int": "int32_t"}
SIGNATURE_CHARS = {"uint": "u", "int": "i"}


class ProtocolError(RuntimeError):
    """Raised when the XML cannot be translated exactly."""


def fnv1a64(data):
    """Cheap fingerprint identifying the exact file the bindings came from."""
    digest = 0xCBF29CE484222325
    for byte in data:
        digest ^= byte
        digest = (digest * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return digest


def macro(*parts):
    return "_".join(parts).upper()


def _signature(member, where):
    """wayland signature string for a request/event.

    Arguments contribute one type letter each.  A message introduced in a later
    interface version carries that version as a *leading* digit -- this is
    wayland-scanner's own encoding (wl_surface.damage_buffer, since 4, is
    "4iiii"; wl_pointer.release, since 3, is "3"), not a trailing one.
    """
    signature = ""
    for arg in member.findall("arg"):
        arg_type = arg.get("type")
        if arg_type not in SCALAR_TYPES:
            raise ProtocolError(
                "%s %r: argument %r has type %r, which this generator does not "
                "translate; extend test_package/e2e/gen_protocol.py before using "
                "such a protocol" % (where, member.get("name"), arg.get("name"), arg_type))
        if not arg.get("name"):
            raise ProtocolError("%s %r: an argument has no name" % (where, member.get("name")))
        signature += SIGNATURE_CHARS[arg_type]
    since = int(member.get("since", "1"))
    if since > 1:
        signature = str(since) + signature
    return signature


def parse(xml_path):
    """Read the package's XML into the shapes the renderers need."""
    if not os.path.isfile(xml_path):
        raise ProtocolError("the package did not deliver the protocol XML: %s" % xml_path)
    with open(xml_path, "rb") as handle:
        raw = handle.read()
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise ProtocolError("%s is not well-formed XML: %s" % (xml_path, exc))
    if root.tag != "protocol":
        raise ProtocolError("%s root element is <%s>, expected <protocol>" % (xml_path, root.tag))

    declared = [node.get("name") for node in root.findall("interface")]
    interfaces = [node for node in root.findall("interface")
                  if node.get("name") == IFACE_NAME]
    if len(interfaces) != 1:
        raise ProtocolError("%s declares interfaces %s; exactly one %s is expected"
                            % (xml_path, declared, IFACE_NAME))
    interface = interfaces[0]

    version = int(interface.get("version", "1"))
    if version != INTERFACE_VERSION:
        raise ProtocolError("%s declares %s version %d, the flow expects %d"
                            % (xml_path, IFACE_NAME, version, INTERFACE_VERSION))

    enums = []
    for enum in interface.findall("enum"):
        entries = []
        for entry in enum.findall("entry"):
            if entry.get("name") is None or entry.get("value") is None:
                raise ProtocolError("%s: enum %s has an entry without name/value"
                                    % (xml_path, enum.get("name")))
            entries.append((entry.get("name"), int(entry.get("value"))))
        if entries:
            enums.append((enum.get("name"), entries))

    requests = []
    for opcode, member in enumerate(node for node in interface.findall("request")
                                    if node.get("name")):
        requests.append({
            "name": member.get("name"),
            "opcode": opcode,
            "signature": _signature(member, "request"),
            "destructor": member.get("type") == "destructor",
            "args": [(SCALAR_TYPES[arg.get("type")], arg.get("name"))
                     for arg in member.findall("arg")],
        })

    events = []
    for opcode, member in enumerate(node for node in interface.findall("event")
                                    if node.get("name")):
        events.append({
            "name": member.get("name"),
            "opcode": opcode,
            "signature": _signature(member, "event"),
            "args": [(SCALAR_TYPES[arg.get("type")], arg.get("name"))
                     for arg in member.findall("arg")],
        })

    if not requests or not events:
        raise ProtocolError("%s: %s declares %d requests and %d events"
                            % (xml_path, IFACE_NAME, len(requests), len(events)))
    # The messages the flow drives must exist, otherwise the generated code would
    # not match plasma_e2e.c.
    if not any(item["name"] == "fetchStates" for item in requests):
        raise ProtocolError("%s: %s has no fetchStates request" % (xml_path, IFACE_NAME))
    if not any(item["name"] == "stateChanged" for item in events):
        raise ProtocolError("%s: %s has no stateChanged event" % (xml_path, IFACE_NAME))

    return {"path": xml_path, "raw": raw, "version": version,
            "enums": enums, "requests": requests, "events": events}


def _render_header(proto):
    path = proto["path"]
    lines = [
        "/* Generated by test_package/e2e/gen_protocol.py from the protocol XML",
        " * that plasma-wayland-protocols installs; do not edit.  The build",
        " * regenerates it and fails when the XML is missing, malformed, or cannot",
        " * be translated exactly.",
        " *",
        " *   source: %s" % path,
        " *   sha256: %s" % hashlib.sha256(proto["raw"]).hexdigest(),
        " *   fnv1a64: 0x%016x" % fnv1a64(proto["raw"]),
        " */",
        "#ifndef KEYSTATE_PROTOCOL_H_GENERATED",
        "#define KEYSTATE_PROTOCOL_H_GENERATED",
        "",
        "#include <stdint.h>",
        "#include <wayland-util.h>",
        "#include <wayland-client-core.h>",
        "#include <wayland-client-protocol.h>",
        "#include <wayland-server-core.h>",
        "",
        "#ifdef __cplusplus",
        'extern "C" {',
        "#endif",
        "",
        "#define KEYSTATE_XML_FNV1A64 0x%016xULL" % fnv1a64(proto["raw"]),
        "",
    ]

    for enum_name, entries in proto["enums"]:
        lines.append("enum %s_%s {" % (IFACE_NAME, enum_name))
        for entry_name, value in entries:
            lines.append("\t%s = %d," % (macro(IFACE_NAME, enum_name, entry_name), value))
        lines.append("};")
        lines.append("")

    lines.append("struct %s;" % IFACE_NAME)
    lines.append("extern const struct wl_interface %s_interface;" % IFACE_NAME)
    lines.append("")
    for item in proto["requests"]:
        lines.append("#define %s %d" % (macro(IFACE_NAME, item["name"]), item["opcode"]))
    for item in proto["events"]:
        lines.append("#define %s %d" % (macro(IFACE_NAME, item["name"]), item["opcode"]))
    lines.append("")

    # --- client side ---------------------------------------------------------
    lines.append("struct %s_listener {" % IFACE_NAME)
    for item in proto["events"]:
        params = ", ".join(["void *data", "struct %s *%s" % (IFACE_NAME, IFACE_NAME)]
                           + ["%s %s" % arg for arg in item["args"]])
        lines.append("\tvoid (*%s)(%s);" % (item["name"], params))
    lines.append("};")
    lines.append("")
    lines.append("static inline int %s_add_listener(struct %s *%s, "
                 "const struct %s_listener *listener, void *data)"
                 % (IFACE_NAME, IFACE_NAME, IFACE_NAME, IFACE_NAME))
    lines.append("{")
    lines.append("\treturn wl_proxy_add_listener((struct wl_proxy *) %s," % IFACE_NAME)
    lines.append("\t\t\t\t     (void (**)(void)) listener, data);")
    lines.append("}")
    lines.append("")
    for item in proto["requests"]:
        params = ", ".join(["struct %s *%s" % (IFACE_NAME, IFACE_NAME)]
                           + ["%s %s" % arg for arg in item["args"]])
        flag = "WL_MARSHAL_FLAG_DESTROY" if item["destructor"] else "0"
        lines.append("static inline void %s_%s(%s)" % (IFACE_NAME, item["name"], params))
        lines.append("{")
        lines.append("\twl_proxy_marshal_flags((struct wl_proxy *) %s," % IFACE_NAME)
        lines.append("\t\t\t     %s, NULL," % macro(IFACE_NAME, item["name"]))
        lines.append("\t\t\t     wl_proxy_get_version((struct wl_proxy *) %s), %s);"
                     % (IFACE_NAME, flag))
        lines.append("}")
        lines.append("")

    # --- server side ---------------------------------------------------------
    lines.append("struct %s_interface {" % IFACE_NAME)
    for item in proto["requests"]:
        params = ", ".join(["struct wl_client *client", "struct wl_resource *resource"]
                           + ["%s %s" % arg for arg in item["args"]])
        lines.append("\tvoid (*%s)(%s);" % (item["name"], params))
    lines.append("};")
    lines.append("")
    for item in proto["events"]:
        params = ", ".join(["struct wl_resource *resource"]
                           + ["%s %s" % arg for arg in item["args"]])
        lines.append("static inline void %s_send_%s(%s)"
                     % (IFACE_NAME, item["name"], params))
        lines.append("{")
        escaped = ", ".join([macro(IFACE_NAME, item["name"])]
                            + [arg[1] for arg in item["args"]])
        lines.append("\twl_resource_post_event(resource, %s);" % escaped)
        lines.append("}")
        lines.append("")

    lines.append("#ifdef __cplusplus")
    lines.append("}")
    lines.append("#endif")
    lines.append("")
    lines.append("#endif /* KEYSTATE_PROTOCOL_H_GENERATED */")
    return "\n".join(lines) + "\n"


def _render_source(proto):
    # No argument of this protocol carries an interface pointer, so the type
    # table only needs a placeholder (wayland-scanner emits the same shape for
    # messages without interface arguments).
    lines = [
        '#include "keystate-protocol.h"',
        "",
        "static const struct wl_interface *%s_types[] = { NULL };" % IFACE_NAME,
        "",
        "static const struct wl_message %s_requests[] = {" % IFACE_NAME,
    ]
    for item in proto["requests"]:
        lines.append('\t{ "%s", "%s", %s_types + 0 },'
                     % (item["name"], item["signature"], IFACE_NAME))
    lines.append("};")
    lines.append("")
    lines.append("static const struct wl_message %s_events[] = {" % IFACE_NAME)
    for item in proto["events"]:
        lines.append('\t{ "%s", "%s", %s_types + 0 },'
                     % (item["name"], item["signature"], IFACE_NAME))
    lines.append("};")
    lines.append("")
    lines.append("WL_EXPORT const struct wl_interface %s_interface = {" % IFACE_NAME)
    lines.append('\t"%s", %d,' % (IFACE_NAME, proto["version"]))
    lines.append("\t%d, %s_requests," % (len(proto["requests"]), IFACE_NAME))
    lines.append("\t%d, %s_events," % (len(proto["events"]), IFACE_NAME))
    lines.append("};")
    return "\n".join(lines) + "\n"


def generate(xml_path, out_dir):
    """Emit keystate-protocol.h/.c into out_dir, or raise ProtocolError."""
    proto = parse(xml_path)
    os.makedirs(out_dir, exist_ok=True)
    header = os.path.join(out_dir, "keystate-protocol.h")
    source = os.path.join(out_dir, "keystate-protocol.c")
    with open(header, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(_render_header(proto))
    with open(source, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(_render_source(proto))
    for path in (header, source):
        if os.path.getsize(path) == 0:
            raise ProtocolError("generator produced an empty file: %s" % path)
    sys.stderr.write("[gen_protocol.py] %s -> %s (%s v%d, fnv1a64=0x%016x)\n"
                     % (xml_path, out_dir, IFACE_NAME, proto["version"],
                        fnv1a64(proto["raw"])))
    return header, source


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: gen_protocol.py <keystate.xml> <output-dir>\n")
        return 2
    try:
        generate(argv[1], argv[2])
    except ProtocolError as exc:
        sys.stderr.write("gen_protocol.py: FAIL: %s\n" % exc)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
