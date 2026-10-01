#!/usr/bin/env python3
"""Pure-Python replacement for the debsig-verify `rsop` binary.

`debian/tests/verify-one` (the package's single upstream autopkgtest, declared
`Depends: @, rsop` in debian/tests/control) ends in

    rsop verify <plaintext signature.asc "$root"/debian-tag2upload.pgp

Note the `<plaintext`: that is a shell input redirection, so rsop receives the
signed data on stdin and two operands, the signature and the keyring.

`rsop` is not present in the OHOS toolchain or in this repository's artifact
store. archives/d/debsig-verify/0.34 documents the same gap: its atlocal.in
probes sqop/rsop/gosop/pgpainless-cli/sq/gpg in order and every candidate is
absent on the device. This module implements the `rsop verify` contract so the
upstream test can run unmodified, with no root, no network and no GnuPG.

The cryptography is real, not a stub:
  * RFC 4880 packet parsing (old- and new-format headers, length types 0/1/2)
  * RFC 4880 5.2.4 v4 signed-data construction, i.e.
        H( data || 0x04 sigtype pk_algo hash_algo
                || uint16(len(hashed_subpackets)) || hashed_subpackets
                || 0x04 0xFF || uint32(6 + len(hashed_subpackets)) )
    An OpenPGP signature does not hash the file directly, so comparing the
    signature's digest prefix against a plain file digest is meaningless; this
    construction is what the reference implementation actually computes.
  * RSA EMSA-PKCS1-v1_5 verification with full padding validation, not a
    suffix match: 0x00 0x01, at least eight 0xFF octets, a 0x00 separator, the
    DER DigestInfo for the declared algorithm, then the digest.
  * Issuer resolution through the hashed issuer-fingerprint subpacket (type 33)
    with a fallback to the unhashed issuer key id (type 16).

Cross-checked against GnuPG 2.4.5 on the upstream fixture: `gpg --verify`
reports a good signature, and every mutation of the plaintext, the signature or
the keyring that this module rejects is also reported BAD by GnuPG. The
construction is the same one already used by the in-tree
archives/d/debsig-verify/0.34/hmbs_gpg_shim.py (rsa_verify/v4_sig_hash).

Usage:  rsop verify <signaturefile> <keyringfile>   (signed data on stdin)
Exit status: 0 = good signature, 1 = unverifiable or bad.
"""

import base64
import hashlib
import struct
import sys

# hash algo id -> (hashlib name, digest length, DER DigestInfo prefix)
HASH_ALGOS = {
    2: ("sha1", 20, bytes.fromhex("3021300906052b0e03021a05000414")),
    8: ("sha256", 32, bytes.fromhex("3031300d060960864801650304020105000420")),
    9: ("sha384", 48, bytes.fromhex("3041300d060960864801650304020205000430")),
    10: ("sha512", 64, bytes.fromhex("3051300d060960864801650304020305000440")),
    11: ("sha224", 28, bytes.fromhex("302d300d06096086480165030402040500041c")),
}

SIGTYPE_BINARY = 0x00
SIGTYPE_CANONICAL_TEXT = 0x01
PK_ALGO_RSA = (1, 3)


class VerifyError(Exception):
    pass


def iter_packets(data):
    i = 0
    total = len(data)
    while i < total:
        ctb = data[i]
        if not ctb & 0x80:
            raise VerifyError(
                "packet header 0x%02x at offset %d has bit 7 clear" % (ctb, i))
        if ctb & 0x40:
            tag = ctb & 0x3F
            i += 1
            if i >= total:
                raise VerifyError("truncated packet length octet")
            first = data[i]
            if first < 192:
                length = first
                i += 1
            elif first < 224:
                if i + 1 >= total:
                    raise VerifyError("truncated two-octet length")
                length = ((first - 192) << 8) + data[i + 1] + 192
                i += 2
            elif first == 255:
                if i + 4 >= total:
                    raise VerifyError("truncated five-octet length")
                length = int.from_bytes(data[i + 1:i + 5], "big")
                i += 5
            else:
                raise VerifyError("partial body lengths are not supported")
        else:
            tag = (ctb & 0x3C) >> 2
            length_type = ctb & 0x03
            i += 1
            if length_type == 0:
                if i >= total:
                    raise VerifyError("truncated one-octet length")
                length = data[i]
                i += 1
            elif length_type == 1:
                if i + 1 >= total:
                    raise VerifyError("truncated two-octet length")
                length = int.from_bytes(data[i:i + 2], "big")
                i += 2
            elif length_type == 2:
                if i + 3 >= total:
                    raise VerifyError("truncated four-octet length")
                length = int.from_bytes(data[i:i + 4], "big")
                i += 4
            else:
                raise VerifyError("indeterminate packet length")
        if i + length > total:
            raise VerifyError(
                "packet %d claims %d octets but only %d remain"
                % (tag, length, total - i))
        yield tag, data[i:i + length]
        i += length


def dearmor(blob):
    if b"-----BEGIN PGP" not in blob:
        return blob
    chunks = []
    inside = False
    for line in blob.splitlines():
        text = line.strip()
        if text.startswith(b"-----BEGIN PGP "):
            inside = True
            continue
        if text.startswith(b"-----END PGP "):
            inside = False
            continue
        if not inside:
            continue
        if not text or text.startswith(b"="):
            continue
        if b": " in text:
            continue
        chunks.append(text)
    try:
        return base64.b64decode(b"".join(chunks), validate=True)
    except Exception as exc:
        raise VerifyError("armored data does not decode: %s" % exc)


def iter_subpackets(blob):
    i = 0
    total = len(blob)
    while i < total:
        length = blob[i]
        i += 1
        if length < 192:
            pass
        elif length < 255:
            if i >= total:
                raise VerifyError("truncated subpacket length")
            length = ((length - 192) << 8) + blob[i] + 192
            i += 1
        else:
            if i + 3 >= total:
                raise VerifyError("truncated subpacket length")
            length = int.from_bytes(blob[i:i + 4], "big")
            i += 4
        if length == 0 or i + length > total:
            raise VerifyError("subpacket length %d overruns the area" % length)
        yield blob[i] & 0x7F, blob[i + 1:i + length]
        i += length


def read_mpi(buf, offset):
    if offset + 2 > len(buf):
        raise VerifyError("truncated MPI length")
    bits = int.from_bytes(buf[offset:offset + 2], "big")
    nbytes = (bits + 7) // 8
    end = offset + 2 + nbytes
    if end > len(buf):
        raise VerifyError("truncated MPI body")
    return int.from_bytes(buf[offset + 2:end], "big"), bits, end


def v4_fingerprint(pubkey_body):
    return hashlib.sha1(
        b"\x99" + struct.pack(">H", len(pubkey_body)) + pubkey_body
    ).hexdigest().upper()


def load_public_keys(keyring_blob):
    keys = []
    for tag, body in iter_packets(keyring_blob):
        if tag != 6:
            continue
        if len(body) < 6 or body[0] != 4:
            continue
        algo = body[5]
        if algo not in PK_ALGO_RSA:
            continue
        try:
            modulus, bits, offset = read_mpi(body, 6)
            exponent, _, _ = read_mpi(body, offset)
        except VerifyError:
            continue
        if bits % 8 or bits < 512 or exponent < 3 or modulus <= 0:
            continue
        keys.append({
            "fpr": v4_fingerprint(body),
            "bits": bits,
            "n": modulus,
            "e": exponent,
        })
    return keys


def parse_signature(sig_body):
    if len(sig_body) < 6 or sig_body[0] != 4:
        raise VerifyError("only v4 signature packets are supported")
    sigtype = sig_body[1]
    pk_algo = sig_body[2]
    hash_algo = sig_body[3]
    hashed_len = int.from_bytes(sig_body[4:6], "big")
    hashed = sig_body[6:6 + hashed_len]
    if len(hashed) != hashed_len:
        raise VerifyError("hashed subpacket area is truncated")
    offset = 6 + hashed_len
    unhashed_len = int.from_bytes(sig_body[offset:offset + 2], "big")
    offset += 2
    unhashed = sig_body[offset:offset + unhashed_len]
    offset += unhashed_len
    left16 = sig_body[offset:offset + 2]
    offset += 2
    sig_int, _, _ = read_mpi(sig_body, offset)
    issuer_fpr = None
    issuer_keyid = None
    for sub_type, sub_data in iter_subpackets(hashed):
        if sub_type == 33 and len(sub_data) == 21 and sub_data[0] == 4:
            issuer_fpr = sub_data[1:].hex().upper()
    for sub_type, sub_data in iter_subpackets(unhashed):
        if sub_type == 16 and len(sub_data) == 8:
            issuer_keyid = sub_data.hex().upper()
    return {
        "sigtype": sigtype,
        "pk_algo": pk_algo,
        "hash_algo": hash_algo,
        "hashed": hashed,
        "left16": left16,
        "sig": sig_int,
        "issuer_fpr": issuer_fpr,
        "issuer_keyid": issuer_keyid,
    }


def find_signature(blob):
    for tag, body in iter_packets(blob):
        if tag == 2:
            return body
    raise VerifyError("no signature packet (tag 2) found")


def canonicalise(data, sigtype):
    if sigtype != SIGTYPE_CANONICAL_TEXT:
        return data
    text = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    text = text.replace(b"\n", b"\r\n")
    if not text.endswith(b"\r\n"):
        text += b"\r\n"
    return text


def signed_digest(data, sig, hash_algo):
    hname = HASH_ALGOS[hash_algo][0]
    prefix = (bytes([4, sig["sigtype"], sig["pk_algo"], hash_algo])
              + struct.pack(">H", len(sig["hashed"]))
              + sig["hashed"])
    trailer = b"\x04\xff" + struct.pack(">I", len(prefix))
    return hashlib.new(hname, canonicalise(data, sig["sigtype"]) + prefix
                       + trailer).digest()


def rsa_pkcs1_verify(sig_int, key, expected_digest, der_prefix):
    modulus = key["n"]
    k = (key["bits"] + 7) // 8
    if sig_int <= 0 or sig_int >= modulus:
        return "signature representative is out of range for the modulus"
    block = pow(sig_int, key["e"], modulus).to_bytes(k, "big")
    if block[0] != 0x00 or block[1] != 0x01:
        return ("recovered block starts 0x%s, expected 0001"
                % block[:2].hex())
    index = 2
    while index < len(block) and block[index] == 0xFF:
        index += 1
    if index >= len(block) or block[index] != 0x00:
        return "no 0x00 separator after the PKCS#1 padding"
    if index - 2 < 8:
        return ("PKCS#1 padding is %d octets, RFC 8017 requires at least 8"
                % (index - 2))
    der = block[index + 1:]
    if not der.startswith(der_prefix):
        return ("DigestInfo DER prefix mismatch: got %s"
                % der[:len(der_prefix)].hex())
    if der[len(der_prefix):] != expected_digest:
        return ("digest mismatch: recovered %s, computed %s"
                % (der[len(der_prefix):].hex(), expected_digest.hex()))
    return None


def verify(data, signature_blob, keyring_blob):
    sig_body = find_signature(signature_blob)
    sig = parse_signature(sig_body)
    if sig["pk_algo"] not in PK_ALGO_RSA:
        raise VerifyError("unsupported public-key algorithm %d" % sig["pk_algo"])
    if sig["hash_algo"] not in HASH_ALGOS:
        raise VerifyError("unsupported hash algorithm %d" % sig["hash_algo"])
    hname, digest_len, der_prefix = HASH_ALGOS[sig["hash_algo"]]
    keys = load_public_keys(keyring_blob)
    if not keys:
        raise VerifyError("keyring contains no usable RSA public key")
    issuer = sig["issuer_fpr"] or sig["issuer_keyid"]
    candidates = [k for k in keys
                  if (sig["issuer_fpr"] and k["fpr"] == sig["issuer_fpr"])
                  or (not sig["issuer_fpr"] and sig["issuer_keyid"]
                      and k["fpr"][-16:] == sig["issuer_keyid"])]
    if not candidates and issuer:
        raise VerifyError(
            "no public key in keyring matches issuer %s (keyring holds %s)"
            % (issuer, ", ".join(k["fpr"] for k in keys)))
    if not candidates:
        candidates = keys
    digest = signed_digest(data, sig, sig["hash_algo"])
    if len(digest) != digest_len:
        raise VerifyError("computed digest has the wrong length")
    rejections = []
    for key in candidates:
        problem = rsa_pkcs1_verify(sig["sig"], key, digest, der_prefix)
        if problem is None:
            if sig["left16"] and sig["left16"] != digest[:2]:
                sys.stderr.write(
                    "rsop: warning: left 16 bits %s differ from digest prefix %s\n"
                    % (sig["left16"].hex(), digest[:2].hex()))
            return key, hname
        rejections.append("%s: %s" % (key["fpr"], problem))
    raise VerifyError("no keyring key validates the signature (%s)"
                      % "; ".join(rejections))


def cmd_verify(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: rsop verify <signaturefile> <keyringfile> "
                         "(signed data is read from stdin)\n")
        return 2
    sig_path, keyring_path = argv
    try:
        data = sys.stdin.buffer.read()
        with open(sig_path, "rb") as handle:
            signature_blob = dearmor(handle.read())
        with open(keyring_path, "rb") as handle:
            keyring_blob = dearmor(handle.read())
        key, hname = verify(data, signature_blob, keyring_blob)
    except (VerifyError, OSError) as exc:
        sys.stderr.write("rsop: verification failed: %s\n" % exc)
        return 1
    sys.stdout.write(
        "rsop: good signature from key %s using %s\n" % (key["fpr"], hname))
    return 0


def main(argv):
    if len(argv) < 2 or argv[1] != "verify":
        sys.stderr.write("rsop: only the 'verify' command is implemented\n")
        return 2
    return cmd_verify(argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
