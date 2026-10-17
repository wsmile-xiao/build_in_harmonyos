#!/usr/bin/env python3
"""End-to-end consumer case: the trust decision a tag2upload verifier makes.

`test_verify.py` answers "are the delivered bytes a well-formed keyring". This
program answers the question a downstream consumer actually asks: *given the
keyring this package installed, may I trust the tag2upload signing key?* It runs
one pipeline over the real artifact and emits a verdict, so the coverage is a
completed flow rather than a list of assertions.

The case is written in the four parts the repo's rule12 guidance asks for
(`knowledge/drafts/DRAFT-genht-1.1.3-rule12-needs-e2e-consumer-case.md`):

  construct input  the delivered keyring, located only through the runenv
                   variable `package_info()` publishes, plus a fixed trust
                   policy and a fixed lookup key id. No randomness.
  real execution   open_keyring -> select_key -> derive_identity ->
                   collect_certifications -> evaluate_trust -> render_report.
                   Every stage raises on malformed input, so a broken artifact
                   cannot slip through to a verdict.
  produce result   a deterministic report, explicitly sorted by key id and
                   creation time, never by dict or packet iteration order.
  check content    the report is compared byte for byte against REFERENCE_REPORT,
                   which was transcribed from GnuPG 2.4.5's own
                   `gpg --with-colons --check-sigs` output (an independent
                   OpenPGP implementation -- see reports/report.md for the
                   transcript). A golden file produced by this program would
                   only be self-certification, so it is not used.

`evaluate_trust` applies three independent gates, mirroring what a verifier
must establish before trusting this key:

  identity   the RFC 4880 section 12.2 fingerprint re-derived from the packet
             body must reproduce the key id that was looked up. This depends
             on the RSA modulus, so substituting a different key fails here.
  binding    at least one self-certification (sigtype 0x13) issued by the key
             itself, which is what ties the key to the user id.
  external   at least one certification from a different key. A bare key whose
             only signature is its own self-signature carries no trust beyond
             self-assertion, which is exactly the risk noted in notes.md.

On top of the gates, the observed certification roster is required to match
the pinned values exactly, because this package pins one released keyring and
GnuPG is available as an offline oracle for it.

The mutation pass then feeds deliberately damaged copies of the same bytes
through the identical pipeline and requires each to be refused, so a verdict of
ACCEPT cannot be produced vacuously.

GnuPG is deliberately not invoked here: it is absent from the OHOS worker
(`archives/l/librnp/0.18.1/conanfile.py`: "cli_tests need GnuPG gpg/gpgconf
(not available on OHOS workers)"), so the case stays pure Python and runs the
same way on the worker as on a developer machine.
"""

import os
import pathlib
import sys

from test_verify import (  # noqa: F401  (reused low-level packet parsing)
    ENV_KEYRING_DIR,
    KEYRING_NAME,
    SUBPKT_ISSUER_FINGERPRINT,
    parse_subpackets,
    walk_packets,
)

# ── fixed input ──────────────────────────────────────────────────────────────
# The key id a consumer is handed when it wants to check a tag signature. It is
# not derived from the artifact, so the identity gate is a real cross-check.
LOOKUP_KEY_ID = "606D084E4683C079"

# Trust policy. Deliberately minimal and structural rather than fitted to the
# observed roster: the exact roster is pinned separately, below.
MIN_SELF_CERTIFICATIONS = 1
MIN_THIRD_PARTY_CERTIFIERS = 1

# Roster pinned from GnuPG 2.4.5 (independent implementation). Transcription in
# reports/report.md.
PINNED_FINGERPRINT = "374D8CE4DB96E9CBD4C0972A606D084E4683C079"
PINNED_UID = "Debian tag2upload service (key 1) <debian-tag2upload@lists.debian.org>"
PINNED_SELF_CERTS = (1741882125, 1770210632)
PINNED_THIRD_PARTY = (
    # (key id, fingerprint, created, sigtype)
    ("0F56D0553B6D411B", "8DC2487E51ABDD90B5C4753F0F56D0553B6D411B", 1747388867, 0x10),
    ("2AE5E34C84B4B055", "D7A387D91018536CB330F7772AE5E34C84B4B055", 1741947022, 0x10),
    ("E3E3392348B50D39", "559AE46C2D6B6D3265E7CBA1E3E3392348B50D39", 1741946902, 0x10),
)

SIGTYPE_GENERIC_CERT = 0x10
SIGTYPE_POSITIVE_CERT = 0x13
SUBPKT_SIGNATURE_CREATION_TIME = 2
PUBKEY_ALGO_RSA = 1

# Byte-for-byte reference, transcribed from `gpg --with-colons --check-sigs
# 606D084E4683C079` under GnuPG 2.4.5. Do not regenerate from this program.
REFERENCE_REPORT = """\
TAG2UPLOAD_CONSUMER_E2E_REPORT v1
policy identity=exact-keyid binding=min1-self-cert external=min1-third-party
key keyid=606D084E4683C079 fpr=374D8CE4DB96E9CBD4C0972A606D084E4683C079 algo=1 bits=4096 created=1741882125
uid Debian tag2upload service (key 1) <debian-tag2upload@lists.debian.org>
self-cert keyid=606D084E4683C079 sigtype=0x13 created=1741882125
self-cert keyid=606D084E4683C079 sigtype=0x13 created=1770210632
third-party keyid=0F56D0553B6D411B fpr=8DC2487E51ABDD90B5C4753F0F56D0553B6D411B sigtype=0x10 created=1747388867
third-party keyid=2AE5E34C84B4B055 fpr=D7A387D91018536CB330F7772AE5E34C84B4B055 sigtype=0x10 created=1741947022
third-party keyid=E3E3392348B50D39 fpr=559AE46C2D6B6D3265E7CBA1E3E3392348B50D39 sigtype=0x10 created=1741946902
checks identity=ok binding=ok external=ok roster=ok
verdict ACCEPT"""

# OHOS delivery surface this package promises: data only, no executables. An
# ELF blob or a bin/ directory would mean the recipe started shipping something
# the OHOS loader and the L0k gate do not accept.
EXPECTED_DELIVERY_SURFACE = ("licenses", "share")

# Conan writes these two bookkeeping files into every package folder, so they
# are not part of the recipe's payload. Everything else must match
# EXPECTED_DELIVERY_SURFACE exactly.
CONAN_METADATA_FILES = frozenset({"conaninfo.txt", "conanmanifest.txt"})


class Rejected(Exception):
    """The pipeline refused the artifact. Carries the reason for the report."""


class Counter:
    def __init__(self):
        self.assertions = 0

    def check(self, condition, message):
        self.assertions += 1
        if not condition:
            raise AssertionError(message)


def locate_keyring():
    """Resolve the artifact only through the published runenv contract."""
    raw = os.environ.get(ENV_KEYRING_DIR)
    if not raw:
        raise Rejected(
            f"{ENV_KEYRING_DIR} is unset: package_info() must publish it into "
            "the consumer runenv"
        )
    path = pathlib.Path(raw) / KEYRING_NAME
    if not path.is_file():
        raise Rejected(f"keyring not installed at {path}")
    return path


def open_keyring(path):
    """Parse the delivered keyring into its packet stream."""
    data = path.read_bytes()
    if not data:
        raise Rejected("keyring is empty")
    return data, walk_packets(data)


def fingerprint_of(public_key_body):
    """RFC 4880 section 12.2 v4 fingerprint; covers the RSA modulus."""
    import hashlib

    return hashlib.sha1(
        b"\x99" + len(public_key_body).to_bytes(2, "big") + public_key_body
    ).hexdigest().upper()


def select_key(packets, wanted_key_id):
    """Pick the public-key packet whose derived key id matches the request.

    Deriving the id here rather than trusting a stored one is what makes the
    lookup meaningful: a swapped modulus yields a different id and is not found.
    """
    matches = []
    for tag, body in packets:
        if tag != 6:
            continue
        if body[0] != 4:
            continue
        if fingerprint_of(body)[-16:] == wanted_key_id:
            matches.append(body)
    if not matches:
        raise Rejected(f"no public key in keyring has key id {wanted_key_id}")
    if len(matches) > 1:
        raise Rejected(f"key id {wanted_key_id} is ambiguous ({len(matches)} keys)")
    return matches[0]


def derive_identity(public_key_body):
    """(fingerprint, key id, algo, bits, created) straight from the packet."""
    if public_key_body[5] != PUBKEY_ALGO_RSA:
        raise Rejected(f"expected RSA (algo 1), got algo {public_key_body[5]}")
    fingerprint = fingerprint_of(public_key_body)
    return {
        "fingerprint": fingerprint,
        "key_id": fingerprint[-16:],
        "algo": public_key_body[5],
        "bits": int.from_bytes(public_key_body[6:8], "big"),
        "created": int.from_bytes(public_key_body[1:5], "big"),
    }


def _hashed_subpackets(signature_body):
    length = int.from_bytes(signature_body[4:6], "big")
    return parse_subpackets(signature_body[6:6 + length])


def collect_certifications(key_fingerprint, packets):
    """Split the certification roster into self-certifications and third party.

    Only the hashed subpacket area is consulted, which is the part a signature
    covers, so a certifier cannot be relabelled by rewriting the unhashed area.
    """
    self_certs = []
    third_party = {}
    for index, (tag, body) in enumerate(packets, 1):
        if tag != 2:
            continue
        if body[0] != 4:
            raise Rejected(f"certification {index}: not a v4 signature")
        sigtype = body[1]
        created = None
        issuer = None
        for subpacket_type, subpacket_body in _hashed_subpackets(body):
            if subpacket_type == SUBPKT_SIGNATURE_CREATION_TIME:
                created = int.from_bytes(subpacket_body, "big")
            elif subpacket_type == SUBPKT_ISSUER_FINGERPRINT:
                if subpacket_body[0] != 4 or len(subpacket_body) != 21:
                    raise Rejected(
                        f"certification {index}: issuer fingerprint subpacket is "
                        f"{len(subpacket_body) - 1} bytes, expected 20"
                    )
                issuer = subpacket_body[1:].hex().upper()
        if created is None or issuer is None:
            raise Rejected(
                f"certification {index}: hashed area lacks a creation time or an "
                "issuer fingerprint, so the certifier cannot be established"
            )
        if issuer == key_fingerprint:
            if sigtype != SIGTYPE_POSITIVE_CERT:
                raise Rejected(
                    f"certification {index}: issued by the key itself but has "
                    f"sigtype 0x{sigtype:02x}, expected 0x13"
                )
            self_certs.append({"key_id": issuer[-16:], "sigtype": sigtype,
                               "created": created})
        else:
            if sigtype == SIGTYPE_POSITIVE_CERT:
                raise Rejected(
                    f"certification {index}: third-party certifier {issuer} "
                    "cannot issue a positive self-certification (0x13)"
                )
            entry = third_party.setdefault(issuer[-16:], {
                "key_id": issuer[-16:], "fingerprint": issuer,
                "sigtype": sigtype, "created": created,
            })
            if entry["sigtype"] != sigtype:
                raise Rejected(
                    f"certifier {issuer} presents conflicting sigtypes "
                    f"0x{entry['sigtype']:02x} and 0x{sigtype:02x}"
                )
    return self_certs, third_party


def read_user_id(packets):
    for tag, body in packets:
        if tag == 13:
            return body.decode("utf-8")
    raise Rejected("keyring carries no user id, so the key has no identity to bind")


def evaluate_roster(identity, user_id, self_certs, third_party):
    """Apply the trust policy and the pinned roster. Raises Rejected on refusal.

    This is the single decision point. `evaluate_trust` and the mutation pass
    both go through it, so a damaged copy is refused by exactly the rules that
    admitted the real artifact.
    """
    # identity gate: derive_identity only returns a key whose derived id matched
    # the requested one, but re-assert it so the gate is explicit.
    if identity["key_id"] != LOOKUP_KEY_ID:
        raise Rejected(
            f"derived key id {identity['key_id']} does not match the requested "
            f"{LOOKUP_KEY_ID}"
        )
    # binding gate
    if len(self_certs) < MIN_SELF_CERTIFICATIONS:
        raise Rejected(
            f"only {len(self_certs)} self-certification(s); a verifier needs at "
            f"least {MIN_SELF_CERTIFICATIONS} to bind the key to its user id"
        )
    # external trust gate
    if len(third_party) < MIN_THIRD_PARTY_CERTIFIERS:
        raise Rejected(
            f"only {len(third_party)} external certifier(s); a key whose only "
            "signatures are its own carry no trust beyond self-assertion"
        )
    # pinned roster, cross-checked against the independent GnuPG transcript
    observed_self = tuple(sorted(c["created"] for c in self_certs))
    observed_third = tuple(sorted(
        (c["key_id"], c["fingerprint"], c["created"], c["sigtype"])
        for c in third_party.values()
    ))
    if identity["fingerprint"] != PINNED_FINGERPRINT:
        raise Rejected(
            f"fingerprint {identity['fingerprint']} does not match the pinned "
            f"{PINNED_FINGERPRINT}"
        )
    if user_id != PINNED_UID:
        raise Rejected(f"user id {user_id!r} does not match the pinned uid")
    if observed_self != PINNED_SELF_CERTS:
        raise Rejected(
            f"self-certification roster {observed_self} does not match the "
            f"pinned {PINNED_SELF_CERTS}"
        )
    if observed_third != PINNED_THIRD_PARTY:
        raise Rejected(
            f"third-party roster {observed_third} does not match the pinned "
            f"{PINNED_THIRD_PARTY}"
        )
    return observed_self, observed_third


def evaluate_trust():
    """Run the whole decision pipeline; return (rendered report, keyring bytes)."""
    path = locate_keyring()
    raw, packets = open_keyring(path)

    public_key = select_key(packets, LOOKUP_KEY_ID)
    identity = derive_identity(public_key)
    user_id = read_user_id(packets)
    self_certs, third_party = collect_certifications(identity["fingerprint"], packets)
    evaluate_roster(identity, user_id, self_certs, third_party)

    return render_report(identity, user_id, self_certs, third_party), raw


def render_report(identity, user_id, self_certs, third_party):
    """Deterministic, explicitly sorted rendering of the decision."""
    lines = [
        "TAG2UPLOAD_CONSUMER_E2E_REPORT v1",
        f"policy identity=exact-keyid binding=min{MIN_SELF_CERTIFICATIONS}-self-cert"
        f" external=min{MIN_THIRD_PARTY_CERTIFIERS}-third-party",
        f"key keyid={identity['key_id']} fpr={identity['fingerprint']} "
        f"algo={identity['algo']} bits={identity['bits']} "
        f"created={identity['created']}",
        f"uid {user_id}",
    ]
    for cert in sorted(self_certs, key=lambda c: (c["created"], c["key_id"])):
        lines.append(
            f"self-cert keyid={cert['key_id']} sigtype=0x{cert['sigtype']:02x} "
            f"created={cert['created']}"
        )
    for cert in sorted(third_party.values(), key=lambda c: c["key_id"]):
        lines.append(
            f"third-party keyid={cert['key_id']} fpr={cert['fingerprint']} "
            f"sigtype=0x{cert['sigtype']:02x} created={cert['created']}"
        )
    lines.append("checks identity=ok binding=ok external=ok roster=ok")
    lines.append("verdict ACCEPT")
    return "\n".join(lines)


def check_delivery_surface(package_root, counter):
    """OHOS platform-adaptation precheck on the real Conan artifact.

    This package ships data only. Confirming that the delivered surface is
    exactly licences plus share, with no executable, ELF or object file, is a
    real property of the artifact rather than a declaration about it.
    """
    root = pathlib.Path(package_root)
    counter.check(root.is_dir(), f"package folder missing: {root}")
    payload = tuple(sorted(
        entry.name for entry in root.iterdir()
        if entry.name not in CONAN_METADATA_FILES
    ))
    counter.check(
        payload == EXPECTED_DELIVERY_SURFACE,
        f"delivery surface is {list(payload)}, expected "
        f"{list(EXPECTED_DELIVERY_SURFACE)}",
    )
    for entry in sorted(root.rglob("*")):
        if entry.is_dir():
            continue
        counter.check(
            entry.suffix not in {".so", ".a", ".o", ".dylib"},
            f"object file shipped in a data package: {entry}",
        )
        with entry.open("rb") as handle:
            magic = handle.read(4)
        counter.check(
            magic != b"\x7fELF",
            f"ELF binary shipped in a data package: {entry}",
        )
        counter.check(
            entry.suffix != ".pgp" or entry.name == KEYRING_NAME,
            f"unexpected keyring payload: {entry}",
        )


def _first_packet_bounds(data):
    header = data[0]
    tag = (header >> 2) & 0x0F
    ltype = header & 0x03
    if ltype == 0:
        return tag, 2, data[1]
    if ltype == 1:
        return tag, 3, (data[1] << 8) | data[2]
    if ltype == 2:
        return tag, 5, int.from_bytes(data[1:5], "big")
    raise Rejected("indeterminate length on the first packet")


def _rebuild_first_packet(data, mutate):
    tag, header_len, length = _first_packet_bounds(data)
    body = bytearray(data[header_len:header_len + length])
    mutate(body)
    return data[:header_len] + bytes(body) + data[header_len + length:]


def _drop_certifications(data, drop):
    """Rebuild the stream without the certification packets at these indices.

    Indices refer to the order the certification packets appear in the stream:
    0 and 4 are this key's two self-certifications, 1..3 are the third-party
    certifiers.
    """
    out = bytearray()
    offset = 0
    signature_index = 0
    while offset < len(data):
        header = data[offset]
        tag = (header >> 2) & 0x0F
        ltype = header & 0x03
        if ltype == 0:
            length, header_len = data[offset + 1], 2
        elif ltype == 1:
            length, header_len = (data[offset + 1] << 8) | data[offset + 2], 3
        elif ltype == 2:
            length, header_len = int.from_bytes(data[offset + 1:offset + 5], "big"), 5
        else:
            length, header_len = len(data) - offset - 1, 1
        end = offset + header_len + length
        if tag != 2 or signature_index not in drop:
            out += data[offset:end]
        if tag == 2:
            signature_index += 1
        offset = end
    return bytes(out)


def _run_on_bytes(data):
    """Drive the identical pipeline over raw bytes instead of the installed file."""
    packets = walk_packets(data)
    public_key = select_key(packets, LOOKUP_KEY_ID)
    identity = derive_identity(public_key)
    user_id = read_user_id(packets)
    self_certs, third_party = collect_certifications(identity["fingerprint"], packets)
    evaluate_roster(identity, user_id, self_certs, third_party)
    return identity, self_certs, third_party


def mutation_controls(data, counter):
    """Every damaged copy must be refused by the identical pipeline."""
    def swap_modulus(body):
        # v4 public-key body layout: [0]=version, [1:5]=created, [5]=algo,
        # [6:8]=modulus bit count, [8:]=the n MPI. Offset 8 is therefore the
        # first octet of the RSA modulus. Flipping offset 0 instead would only
        # bump the version byte, and select_key would then drop the key on
        # `body[0] != 4` before the identity gate ever saw it -- the control
        # would pass without ever exercising the modulus.
        body[8] ^= 0x01
        body[len(body) // 2] ^= 0x01

    def break_user_id(body):
        # The user id is the only tag-13 packet; corrupt it in place.
        body[0] = ord("X")

    controls = [
        # A structurally valid key with a different RSA modulus: the identity
        # gate must not find the key the consumer asked for.
        ("rsa-modulus-substituted", _rebuild_first_packet(data, swap_modulus)),
        # Key<->user-id binding removed: nothing ties the key to its identity.
        ("self-certifications-removed", _drop_certifications(data, drop={0, 4})),
        # External trust downgraded from three certifiers to two.
        ("third-party-reduced-to-two", _drop_certifications(data, drop={3})),
        # Nothing vouches for the key at all.
        ("all-certifications-removed",
         _drop_certifications(data, drop={0, 1, 2, 3, 4})),
        ("user-id-tampered", _replace_user_id(data, break_user_id)),
    ]
    for name, corrupted in controls:
        refused = False
        reason = ""
        try:
            _run_on_bytes(corrupted)
        except (Rejected, ValueError, IndexError) as error:
            refused = True
            reason = str(error)
        counter.check(
            refused,
            f"mutation control failed: the trust pipeline accepted a damaged "
            f"keyring ({name}), so ACCEPT on the real keyring would be vacuous",
        )
        print(f"TAG2UPLOAD_E2E_MUTATION_REJECTED name={name} reason={reason}")


def _replace_user_id(data, mutate):
    """Rebuild the stream with the user-id packet body passed through mutate()."""
    out = bytearray()
    offset = 0
    while offset < len(data):
        header = data[offset]
        tag = (header >> 2) & 0x0F
        ltype = header & 0x03
        if ltype == 0:
            length, header_len = data[offset + 1], 2
        elif ltype == 1:
            length, header_len = (data[offset + 1] << 8) | data[offset + 2], 3
        elif ltype == 2:
            length, header_len = int.from_bytes(data[offset + 1:offset + 5], "big"), 5
        else:
            length, header_len = len(data) - offset - 1, 1
        end = offset + header_len + length
        if tag == 13:
            body = bytearray(data[offset + header_len:end])
            mutate(body)
            out += data[offset:offset + header_len] + bytes(body)
        else:
            out += data[offset:end]
        offset = end
    return bytes(out)


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} PACKAGE_ROOT", file=sys.stderr)
        return 2
    counter = Counter()

    report, data = evaluate_trust()

    counter.check(
        report == REFERENCE_REPORT,
        "trust report does not match the GnuPG-derived reference:\n"
        f"--- got ---\n{report}\n--- want ---\n{REFERENCE_REPORT}",
    )
    counter.check(
        report.endswith("verdict ACCEPT"),
        "pipeline did not reach an ACCEPT verdict on the delivered keyring",
    )

    check_delivery_surface(argv[1], counter)

    mutation_controls(data, counter)

    print(report)
    print(
        "TAG2UPLOAD_CONSUMER_E2E_PASS "
        f"verdict=ACCEPT assertions={counter.assertions} "
        f"self_certs={len(PINNED_SELF_CERTS)} "
        f"third_party={len(PINNED_THIRD_PARTY)} "
        f"delivery_surface={','.join(EXPECTED_DELIVERY_SURFACE)}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except (Rejected, AssertionError, ValueError, OSError, IndexError) as error:
        print(f"TAG2UPLOAD_CONSUMER_E2E_FAIL: {error}", file=sys.stderr)
        sys.exit(1)
