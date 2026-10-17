#!/usr/bin/env python3
"""Consumer validation for the debian-tag2upload-keyring data package.

The package is consumed the way a real consumer consumes it: `package_info()`
injects `OPENPGP_KEYRING_DIR` through the Conan runenv, so the keyring is
located through that variable instead of a hardcoded package-relative path.
That makes the test cover the delivered contract (runenv variable + payload
layout) and not merely the presence of a file.

The located binary keyring is parsed as an OpenPGP old-format packet stream and
checked against the structure Debian publishes for tag 1.2: one v4 RSA public
key, one user ID naming the tag2upload service, and several certification
signatures. The fingerprint and long key id are re-derived with the RFC 4880
v4 rule (SHA-1 over 0x99, the two-octet body length and the whole public-key
body) and are cross-checked against values obtained from `gpg`, so the check
depends on the RSA modulus rather than on the creation timestamp alone.

Each certification is then traced to the certifier key named in its hashed
issuer-fingerprint subpacket, and the observed structure is asserted: the key
carries two self-certifications (sigtype 0x13) plus generic certifications
(0x10) from at least three distinct third-party certifier keys.

Finally a mutation-control pass feeds deliberately corrupted copies of the same
bytes back through the identical validator and requires every one of them to be
rejected. Without that pass a PASS could be vacuously true; with it, a PASS
means the assertions can actually fail.
"""

import hashlib
import os
import pathlib
import sys
import tempfile

ENV_KEYRING_DIR = "OPENPGP_KEYRING_DIR"
KEYRING_NAME = "debian-tag2upload.pgp"

EXPECTED_KEY_ID = "606D084E4683C079"
EXPECTED_FINGERPRINT = "374D8CE4DB96E9CBD4C0972A606D084E4683C079"
EXPECTED_KEY_BITS = 4096
EXPECTED_KEY_CREATED = 1741882125
EXPECTED_UID = "Debian tag2upload service (key 1)"
EXPECTED_SELF_CERTIFICATIONS = 2
MIN_CERTIFICATIONS = 3
MIN_THIRD_PARTY_CERTIFIERS = 3

PUBKEY_ALGO_RSA = 1
SIGTYPE_GENERIC_CERT = 0x10
SIGTYPE_POSITIVE_CERT = 0x13
CERTIFICATION_SIGTYPES = (0x10, 0x11, 0x12, 0x13)
SUBPKT_ISSUER_FINGERPRINT = 33


class Validator:
    def __init__(self):
        self.assertions = 0

    def check(self, condition, message):
        self.assertions += 1
        if not condition:
            raise AssertionError(message)


def parse_old_header(data, offset):
    """Parse an old-format OpenPGP packet header.

    Returns (tag, length, header_len). length is None for the 'indeterminate'
    form, which is only legal for the final packet. Raises ValueError on any
    byte sequence that is not a well-formed old-format packet header; this is
    an explicit raise rather than `assert` so the mutation-control pass keeps
    working under `python -O`.
    """
    header = data[offset]
    if not header & 0x80:
        raise ValueError(
            f"offset {offset}: 0x{header:02x} has bit 7 clear, "
            "not an old-format packet header"
        )
    if header & 0x40:
        raise ValueError(
            f"offset {offset}: 0x{header:02x} has bit 6 set (new-format header), "
            "this keyring must be old-format"
        )
    tag = (header >> 2) & 0x0F
    ltype = header & 0x03
    if ltype == 0:
        return tag, data[offset + 1], 2
    if ltype == 1:
        return tag, (data[offset + 1] << 8) | data[offset + 2], 3
    if ltype == 2:
        return (
            tag,
            (data[offset + 1] << 24)
            | (data[offset + 2] << 16)
            | (data[offset + 3] << 8)
            | data[offset + 4],
            5,
        )
    return tag, None, 1  # indeterminate length (final packet only)


def walk_packets(data):
    """Split an old-format packet stream into (tag, body) pairs.

    Every packet must end inside the stream, and the next packet header must
    begin exactly where the previous packet ended, so trailing garbage or a
    lying length octet is a hard error.
    """
    packets = []
    offset = 0
    while offset < len(data):
        tag, length, header_len = parse_old_header(data, offset)
        if length is None:
            # Indeterminate length consumes the rest of the stream.
            packets.append((tag, data[offset + header_len:]))
            offset = len(data)
            continue
        end = offset + header_len + length
        if end > len(data):
            raise ValueError(
                f"packet {len(packets) + 1} (tag={tag}) claims to end at {end}, "
                f"past end of stream {len(data)}"
            )
        packets.append((tag, data[offset + header_len:end]))
        offset = end
    return packets


def fingerprint_of(public_key_body):
    """Derive the full v4 fingerprint of a public key packet (RFC 4880 §12.2).

    The hash input is 0x99, the two-octet big-endian body length and the whole
    public-key body. Hashing only a slice of the body would make the result
    independent of the RSA modulus, i.e. it would not identify the key.
    """
    return hashlib.sha1(
        b"\x99" + len(public_key_body).to_bytes(2, "big") + public_key_body
    ).hexdigest().upper()


def key_id_of(public_key_body):
    """Derive the long key id of a v4 public key packet (RFC 4880 §12.2)."""
    fingerprint = bytes.fromhex(fingerprint_of(public_key_body))
    return fingerprint[-8:].hex().upper()


def parse_subpackets(area):
    """Parse an OpenPGP signature subpacket area into (type, body) pairs."""
    result = []
    position = 0
    while position < len(area):
        first = area[position]
        if first < 192:
            length, position = first, position + 1
        elif first < 255:
            length = ((first - 192) << 8) + area[position + 1] + 192
            position += 2
        else:
            length = int.from_bytes(area[position + 1:position + 5], "big")
            position += 5
        if length == 0:
            break
        if position + length > len(area):
            raise ValueError(
                f"subpacket of length {length} at {position} runs past "
                f"subpacket area of {len(area)} bytes"
            )
        result.append((area[position] & 0x7F, area[position + 1:position + length]))
        position += length
    return result


def certifier_of(signature_body):
    """Return the issuer fingerprint carried in a certification's hashed area.

    The tag2upload key is shipped as a bare public key with no self-signature,
    so the trust path is carried entirely by third-party certifications. This
    reads the hashed issuer-fingerprint subpacket (type 33) that binds each of
    them to a specific certifier key.
    """
    hashed_length = int.from_bytes(signature_body[4:6], "big")
    area = signature_body[6:6 + hashed_length]
    for subpacket_type, body in parse_subpackets(area):
        if subpacket_type == SUBPKT_ISSUER_FINGERPRINT:
            if body[0] != 4:
                raise ValueError(
                    f"issuer fingerprint subpacket is version {body[0]}, expected 4"
                )
            if len(body) != 21:
                raise ValueError(
                    f"issuer fingerprint is {len(body) - 1} bytes, expected 20"
                )
            return body[1:].hex().upper()
    return None


def validate_keyring(data, validator):
    """Validate the full keyring payload; returns a summary dict."""
    validator.check(len(data) > 0, "keyring stream is empty")

    packets = walk_packets(data)
    pubkeys = [body for tag, body in packets if tag == 6]
    user_ids = [body for tag, body in packets if tag == 13]
    signatures = [body for tag, body in packets if tag == 2]

    validator.check(
        len(packets) >= 3, f"expected a multi-packet keyring, got {len(packets)}"
    )
    validator.check(
        len(pubkeys) == 1, f"expected exactly 1 public-key packet, got {len(pubkeys)}"
    )
    validator.check(
        len(user_ids) == 1, f"expected exactly 1 user-id packet, got {len(user_ids)}"
    )
    validator.check(
        len(signatures) >= MIN_CERTIFICATIONS,
        f"expected >={MIN_CERTIFICATIONS} certification packets, got {len(signatures)}",
    )

    key = pubkeys[0]
    validator.check(key[0] == 4, f"expected v4 public key packet, got version {key[0]}")
    validator.check(
        key[5] == PUBKEY_ALGO_RSA, f"expected RSA public key (algo 1), got {key[5]}"
    )
    bits = int.from_bytes(key[6:8], "big")
    validator.check(
        bits == EXPECTED_KEY_BITS,
        f"expected {EXPECTED_KEY_BITS}-bit RSA key, got {bits}",
    )
    created = int.from_bytes(key[1:5], "big")
    validator.check(
        created == EXPECTED_KEY_CREATED,
        f"expected key creation time {EXPECTED_KEY_CREATED}, got {created}",
    )
    key_fingerprint = fingerprint_of(key)
    validator.check(
        key_fingerprint == EXPECTED_FINGERPRINT,
        f"derived fingerprint {key_fingerprint} does not match expected "
        f"{EXPECTED_FINGERPRINT}",
    )
    key_id = key_id_of(key)
    validator.check(
        key_id == EXPECTED_KEY_ID,
        f"derived key id {key_id} does not match expected {EXPECTED_KEY_ID}",
    )

    # The user-id body is UTF-8 text; tolerate a leading one-octet length
    # prefix by matching on the decoded text rather than on an exact offset.
    uid_text = user_ids[0].decode("utf-8", "replace")
    validator.check(
        EXPECTED_UID in uid_text, f"unexpected user id: {uid_text!r}"
    )

    self_certifications = 0
    third_party = {}
    for index, signature in enumerate(signatures, 1):
        validator.check(
            signature[0] == 4, f"certification {index}: expected v4, got {signature[0]}"
        )
        validator.check(
            signature[1] in CERTIFICATION_SIGTYPES,
            f"certification {index}: sigtype 0x{signature[1]:02x} is not a certification",
        )
        fingerprint = certifier_of(signature)
        validator.check(
            fingerprint is not None,
            f"certification {index} carries no hashed issuer-fingerprint "
            "subpacket, so its certifier cannot be identified",
        )
        if fingerprint == key_fingerprint:
            validator.check(
                signature[1] == SIGTYPE_POSITIVE_CERT,
                f"certification {index} is issued by the key itself but has "
                f"sigtype 0x{signature[1]:02x}, expected a positive "
                "certification (0x13)",
            )
            self_certifications += 1
        else:
            validator.check(
                signature[1] != SIGTYPE_POSITIVE_CERT,
                f"certification {index} claims a positive certification (0x13) "
                f"from third-party certifier {fingerprint}",
            )
            third_party.setdefault(signature[1], set()).add(fingerprint)

    validator.check(
        self_certifications == EXPECTED_SELF_CERTIFICATIONS,
        f"expected {EXPECTED_SELF_CERTIFICATIONS} self-certifications, got "
        f"{self_certifications}",
    )
    certifiers = sorted(set().union(*third_party.values())) if third_party else []
    validator.check(
        len(certifiers) >= MIN_THIRD_PARTY_CERTIFIERS,
        "expected >={} distinct third-party certifier keys, got {}".format(
            MIN_THIRD_PARTY_CERTIFIERS, len(certifiers)
        ),
    )
    validator.check(
        SIGTYPE_GENERIC_CERT in third_party,
        "expected generic third-party certifications (sigtype 0x10), got "
        f"sigtypes {sorted(third_party)}",
    )

    return {
        "packets": len(packets),
        "key_id": key_id,
        "fingerprint": key_fingerprint,
        "key_bits": bits,
        "key_created": created,
        "uid": uid_text,
        "certifications": len(signatures),
        "self_certifications": self_certifications,
        "third_party_certifiers": len(certifiers),
    }


def _replace_first_packet_body(data, mutate):
    """Rebuild the stream with the first packet's body passed through mutate()."""
    _, length, header_len = parse_old_header(data, 0)
    body = bytearray(data[header_len:header_len + length])
    mutate(body)
    return data[:header_len] + bytes(body) + data[header_len + length:]


def _substitute_modulus(data):
    """Same version/creation time/algo/bit-length/public exponent, other modulus.

    This is the substitution that a wrong fingerprint implementation cannot
    see: keeping bytes 0..7 and the trailing exponent MPI intact leaves every
    structural field untouched, so only a key id that actually covers the RSA
    modulus will notice. The low bit of the top modulus byte is flipped, which
    keeps the declared 4096-bit length true.
    """

    def mutate(body):
        body[8] ^= 0x01
        body[len(body) // 2] ^= 0x01

    return _replace_first_packet_body(data, mutate)


def _swap_public_key_algo(data):
    """Re-declare the key as DSA (17) while the body stays an RSA key."""

    def mutate(body):
        body[5] = 17

    return _replace_first_packet_body(data, mutate)


def _shrink_key_bits(data):
    """Halve the declared modulus bit count (4096 -> 2048)."""

    def mutate(body):
        body[6:8] = (2048).to_bytes(2, "big")

    return _replace_first_packet_body(data, mutate)


def _shift_creation_time(data):
    """Move the key's creation time; the key material is untouched."""

    def mutate(body):
        body[1:5] = (EXPECTED_KEY_CREATED - 86400).to_bytes(4, "big")

    return _replace_first_packet_body(data, mutate)


def mutations(data):
    """Corrupted variants of the real bytes, each of which must be rejected."""
    oversized = bytearray(data)
    # First packet uses a two-octet length (ltype 1); inflate it past EOF.
    oversized[1] = 0xFF
    oversized[2] = 0xFF
    return [
        ("truncated-last-byte", data[:-1]),
        ("packet-header-bit7-cleared", bytes([data[0] & 0x7F]) + data[1:]),
        ("first-packet-length-inflated", bytes(oversized)),
        ("rsa-modulus-substituted", _substitute_modulus(data)),
        ("public-key-algo-swapped-to-dsa", _swap_public_key_algo(data)),
        ("key-bits-shrunk-to-2048", _shrink_key_bits(data)),
        ("key-creation-time-shifted", _shift_creation_time(data)),
    ]


def locate_keyring():
    """Resolve the keyring through the runenv contract the recipe publishes."""
    raw = os.environ.get(ENV_KEYRING_DIR)
    if not raw:
        raise AssertionError(
            f"{ENV_KEYRING_DIR} is not set: package_info() must inject it into the "
            "consumer runenv, and the test must be launched with env=\"conanrun\""
        )
    directory = pathlib.Path(raw)
    return directory, directory / KEYRING_NAME


def runenv_controls(validator):
    """The runenv contract itself must be able to fail.

    Without these, a run launched without `env="conanrun"` would abort on the
    very first `locate_keyring()` call and the structural assertions would never
    run, so the contract would be enforced only by an exception rather than by a
    check that can be counted and reported.
    """
    saved = os.environ.get(ENV_KEYRING_DIR)
    try:
        os.environ.pop(ENV_KEYRING_DIR, None)
        refused = False
        try:
            locate_keyring()
        except (AssertionError, ValueError, OSError):
            refused = True
        validator.check(
            refused,
            f"runenv control failed: locate_keyring() accepted a missing "
            f"{ENV_KEYRING_DIR}, so the published contract is not enforced",
        )

        empty = validator
        os.environ[ENV_KEYRING_DIR] = str(pathlib.Path(tempfile.gettempdir()))
        directory, path = locate_keyring()
        empty.check(
            not path.is_file(),
            f"runenv control failed: expected no keyring under {directory}",
        )
    finally:
        if saved is None:
            os.environ.pop(ENV_KEYRING_DIR, None)
        else:
            os.environ[ENV_KEYRING_DIR] = saved


def main(argv):
    if len(argv) != 2:
        print(f"usage: {argv[0]} PACKAGE_ROOT", file=sys.stderr)
        return 2
    validator = Validator()

    runenv_controls(validator)

    directory, path = locate_keyring()
    validator.check(directory.is_dir(), f"{ENV_KEYRING_DIR} is not a directory: {directory}")
    validator.check(path.is_file(), f"missing keyring: {path}")
    data = path.read_bytes()

    summary = validate_keyring(data, validator)

    for name, corrupted in mutations(data):
        rejected = False
        try:
            validate_keyring(corrupted, Validator())
        except (AssertionError, ValueError, IndexError):
            rejected = True
        validator.check(
            rejected,
            f"mutation control failed: validator accepted corrupted keyring ({name}), "
            "so a PASS on the real keyring would be vacuous",
        )

    print(
        "TAG2UPLOAD_KEYRING_VALIDATION_PASS "
        f"packets={summary['packets']} "
        f"assertions={validator.assertions} "
        f"keyid={summary['key_id']} "
        f"fpr={summary['fingerprint']} "
        f"bits={summary['key_bits']} "
        f"created={summary['key_created']} "
        f"uid={summary['uid']!r} "
        f"certifications={summary['certifications']} "
        f"self_certs={summary['self_certifications']} "
        f"third_party_certifiers={summary['third_party_certifiers']} "
        f"keyring_dir={directory}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except (AssertionError, ValueError, OSError, IndexError) as error:
        print(f"TAG2UPLOAD_KEYRING_VALIDATION_FAIL: {error}", file=sys.stderr)
        sys.exit(1)
