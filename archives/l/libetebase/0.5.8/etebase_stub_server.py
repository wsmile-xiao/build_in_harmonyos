#!/usr/bin/env python3
import base64, hashlib, os, struct, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

def b64url_decode(s):
    if isinstance(s, bytes):
        s = s.decode("ascii")
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)

def mp_decode(buf, pos=0):
    b = buf[pos]
    if b <= 0x7F:
        return b, pos + 1
    if b >= 0xE0:
        return struct.unpack("b", bytes([b]))[0], pos + 1
    if (b & 0xE0) == 0xA0:
        n = b & 0x1F
        return buf[pos+1:pos+1+n].decode("utf-8"), pos+1+n
    if (b & 0xF0) == 0x80:
        n = b & 0x0F
        return _mp_map(buf, pos+1, n)
    if (b & 0xF0) == 0x90:
        n = b & 0x0F
        return _mp_arr(buf, pos+1, n)
    if b == 0xC0:
        return None, pos+1
    if b == 0xC2:
        return False, pos+1
    if b == 0xC3:
        return True, pos+1
    if b == 0xC4:
        n = buf[pos+1]
        return bytes(buf[pos+2:pos+2+n]), pos+2+n
    if b == 0xC5:
        n = struct.unpack(">H", buf[pos+1:pos+3])[0]
        return bytes(buf[pos+3:pos+3+n]), pos+3+n
    if b == 0xC6:
        n = struct.unpack(">I", buf[pos+1:pos+5])[0]
        return bytes(buf[pos+5:pos+5+n]), pos+5+n
    if b == 0xCC:
        return buf[pos+1], pos+2
    if b == 0xCD:
        return struct.unpack(">H", buf[pos+1:pos+3])[0], pos+3
    if b == 0xCE:
        return struct.unpack(">I", buf[pos+1:pos+5])[0], pos+5
    if b == 0xCF:
        return struct.unpack(">Q", buf[pos+1:pos+9])[0], pos+9
    if b == 0xD0:
        return struct.unpack("b", buf[pos+1:pos+2])[0], pos+2
    if b == 0xD1:
        return struct.unpack(">h", buf[pos+1:pos+3])[0], pos+3
    if b == 0xD2:
        return struct.unpack(">i", buf[pos+1:pos+5])[0], pos+5
    if b == 0xD3:
        return struct.unpack(">q", buf[pos+1:pos+9])[0], pos+9
    if b == 0xD9:
        n = buf[pos+1]
        return buf[pos+2:pos+2+n].decode("utf-8"), pos+2+n
    if b == 0xDA:
        n = struct.unpack(">H", buf[pos+1:pos+3])[0]
        return buf[pos+3:pos+3+n].decode("utf-8"), pos+3+n
    if b == 0xDB:
        n = struct.unpack(">I", buf[pos+1:pos+5])[0]
        return buf[pos+5:pos+5+n].decode("utf-8"), pos+5+n
    if b == 0xDC:
        n = struct.unpack(">H", buf[pos+1:pos+3])[0]
        return _mp_arr(buf, pos+3, n)
    if b == 0xDD:
        n = struct.unpack(">I", buf[pos+1:pos+5])[0]
        return _mp_arr(buf, pos+5, n)
    if b == 0xDE:
        n = struct.unpack(">H", buf[pos+1:pos+3])[0]
        return _mp_map(buf, pos+3, n)
    if b == 0xDF:
        n = struct.unpack(">I", buf[pos+1:pos+5])[0]
        return _mp_map(buf, pos+5, n)
    raise ValueError("mp 0x%02x at %d" % (b, pos))

def _mp_arr(buf, pos, n):
    out = []
    for _ in range(n):
        v, pos = mp_decode(buf, pos)
        out.append(v)
    return out, pos

def _mp_map(buf, pos, n):
    out = {}
    for _ in range(n):
        k, pos = mp_decode(buf, pos)
        v, pos = mp_decode(buf, pos)
        out[k] = v
    return out, pos

def mp_loads(buf):
    if not buf:
        return None
    v, _ = mp_decode(bytes(buf), 0)
    return v

def mp_encode(obj):
    if obj is None:
        return b"\xc0"
    if obj is True:
        return b"\xc3"
    if obj is False:
        return b"\xc2"
    if isinstance(obj, int):
        if 0 <= obj <= 0x7F:
            return bytes([obj])
        if 0 <= obj <= 0xFF:
            return b"\xcc" + bytes([obj])
        if 0 <= obj <= 0xFFFF:
            return b"\xcd" + struct.pack(">H", obj)
        if 0 <= obj <= 0xFFFFFFFF:
            return b"\xce" + struct.pack(">I", obj)
        return b"\xcf" + struct.pack(">Q", obj & 0xFFFFFFFFFFFFFFFF)
    if isinstance(obj, bytes):
        n = len(obj)
        if n <= 0xFF:
            return b"\xc4" + bytes([n]) + obj
        if n <= 0xFFFF:
            return b"\xc5" + struct.pack(">H", n) + obj
        return b"\xc6" + struct.pack(">I", n) + obj
    if isinstance(obj, str):
        b = obj.encode("utf-8")
        n = len(b)
        if n <= 0x1F:
            return bytes([0xA0 | n]) + b
        if n <= 0xFF:
            return b"\xd9" + bytes([n]) + b
        if n <= 0xFFFF:
            return b"\xda" + struct.pack(">H", n) + b
        return b"\xdb" + struct.pack(">I", n) + b
    if isinstance(obj, (list, tuple)):
        n = len(obj)
        if n <= 0x0F:
            head = bytes([0x90 | n])
        elif n <= 0xFFFF:
            head = b"\xdc" + struct.pack(">H", n)
        else:
            head = b"\xdd" + struct.pack(">I", n)
        return head + b"".join(mp_encode(x) for x in obj)
    if isinstance(obj, dict):
        n = len(obj)
        if n <= 0x0F:
            head = bytes([0x80 | n])
        elif n <= 0xFFFF:
            head = b"\xde" + struct.pack(">H", n)
        else:
            head = b"\xdf" + struct.pack(">I", n)
        out = [head]
        for k, v in obj.items():
            out.append(mp_encode(k))
            out.append(mp_encode(v))
        return b"".join(out)
    raise ValueError("mp enc %r" % type(obj))

_Q = (1 << 255) - 19
_L = (1 << 252) + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _Q - 2, _Q)) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)

def _xrecover(y):
    xx = (y * y - 1) * pow(_D * y * y + 1, _Q - 2, _Q)
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x

_By = (4 * pow(5, _Q - 2, _Q)) % _Q
_Bx = _xrecover(_By)
_BP = (_Bx % _Q, _By % _Q)

def _eadd(p, q):
    x1, y1 = p
    x2, y2 = q
    x3 = (x1*y2 + x2*y1) * pow(1 + _D*x1*x2*y1*y2, _Q-2, _Q)
    y3 = (y1*y2 + x1*x2) * pow(1 - _D*x1*x2*y1*y2, _Q-2, _Q)
    return (x3 % _Q, y3 % _Q)

def _smult(p, e):
    q = (0, 1)
    while e > 0:
        if e & 1:
            q = _eadd(q, p)
        p = _eadd(p, p)
        e >>= 1
    return q

def _decpoint(s):
    y = sum(2**i * ((s[i//8] >> (i % 8)) & 1) for i in range(0, 255))
    x = _xrecover(y)
    if x & 1 != (s[31] >> 7):
        x = _Q - x
    return (x, y)

def ed_verify(sig, msg, pub):
    if len(sig) != 64 or len(pub) != 32:
        return False
    try:
        r = _decpoint(sig[:32])
        a = _decpoint(pub)
        s = int.from_bytes(sig[32:], "little")
        if s >= _L:
            return False
        h = hashlib.sha512(sig[:32] + pub + msg).digest()
        k = int.from_bytes(h, "little") % _L
        return _smult(_BP, s) == _eadd(r, _smult(a, k))
    except Exception:
        return False

def _su(username, email, pubkey, enc, loginPubkey, key, salt):
    return {"username": username, "email": email,
            "pubkey": b64url_decode(pubkey),
            "encryptedContent": b64url_decode(enc),
            "loginPubkey": b64url_decode(loginPubkey),
            "salt": b64url_decode(salt),
            "challenge": None, "token": None}

USERS = {
 "test_user": _su("test_user", "test@localhost",
  "CXNdzeU6FgHz9ei64wJbKDhHc0fkoJ1p_c8zGuFeuGA",
  "wjRGC2jhqYdtF7lO1aS2I5r8gaWx4mZR19_lMZeoNZVU3HbBTqlFC5zZkN-NOO-4cDPZk2xk27GspPLHkOH59-Jk5fAY5hKFT8Vdp0jSgBvKOww-zXXlKfzhkjrReyUSsBwra_NAxGg",
  "A9K94qEAqMm_yrt0wXKwG6H7DDimFIxaRqCpKRrOSuI",
  "Eq9b_rdbzeiU3P4sg5qN24KXbNgy8GgCeC74nFF99hI",
  "6y7jUaojtLq6FISBWPjwXTeiYk5cTiz1oe6HVNGvn2E"),
 "test_user2": _su("test_user2", "test2@localhost",
  "QOZOIEUx2aSnEvrubiHxQ8Tf2UBw6eLea778H0-Bp3g",
  "aomaCuUO5cYXPPxo7SdnvXqBUyqfgx-Hz9YK87e2R7CsfoxzQi1MJGLOfol7S2xXFUmIfSeQLr2Tq4BUBIkitHipDefmr73TP9gV3n-unORW0Vzw0zwpv2I8Aftf2O__DlGk9WfN_NA",
  "h6tXrc783wSW3-TfnI5qg1teJbN5bQRcDE1fjZQ9Y08",
  "AWXkhEFuf_vKquq-vTgHoYRu9NXr0z4ZeScwaLSgoT4",
  "xXfZM3DEiBNqL0pjfGgZSbTU82w9eD1UXUd54LuwMrU"),
}
TOKENS = {}
TSEQ = [0]
CVER = 1
COLLS = {}
GSTOK = [0]

def _nstok():
    GSTOK[0] += 1
    return "st%d" % GSTOK[0]

def _uid(o):
    try:
        u = o.get("uid")
        return u.decode() if isinstance(u, bytes) else u
    except Exception:
        return None

def _norm_str(v):
    try:
        if v is None:
            return None
        if isinstance(v, bytes):
            return v.decode()
        return v
    except Exception:
        return None

def _top_etag(o):
    try:
        return _norm_str(o.get("etag"))
    except Exception:
        return None

def _cuid(o):
    try:
        c = o.get("content")
        if isinstance(c, dict):
            u = c.get("uid")
            return u.decode() if isinstance(u, bytes) else u
    except Exception:
        pass
    return None

class H(BaseHTTPRequestHandler):
    server_version = "EtebaseStub/0.5.8"
    def log_message(self, fmt, *args):
        sys.stderr.write("[stub] %s %s\n" % (self.command, self.path))
        sys.stderr.flush()
    def _send(self, code, body=b""):
        self.send_response(code)
        self.send_header("Content-Type", "application/msgpack")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)
    def _mp(self, code, obj):
        self._send(code, mp_encode(obj))
    def _err(self, code, detail):
        self._mp(code, {"code": "err", "detail": detail})
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n > 0 else b""
    def _user(self):
        a = self.headers.get("Authorization") or ""
        if a.startswith("Token "):
            return TOKENS.get(a[6:].strip())
        return None
    def do_GET(self):
        import urllib.parse as _up
        u = _up.urlparse(self.path)
        path, qs = u.path, _up.parse_qs(u.query)
        if path == "/api/v1/authentication/is_etebase/":
            self._send(200, b"{}")
            return
        if path.startswith("/api/v1/collection/"):
            rest = path[len("/api/v1/collection/"):]
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            parts = [p for p in rest.split("/") if p]
            if len(parts) == 2 and parts[1] == "member":
                # CollectionMemberManagerOnline::list is GET
                # /api/v1/collection/{uid}/member/ and parses
                # IteratorListResponse<CollectionMember> {data,done,iterator}
                # with camelCase {username,accessLevel}; Admin=1
                # (encrypted_models.rs repr ReadOnly=0/Admin=1/ReadWrite=2).
                # It must be answered inside the collection prefix: falling
                # through to the trailing 404 made members NULL and crashed
                # test_basic_invitations (rc=-11).
                c = COLLS.get(parts[0])
                if c is None or c["owner"] != user:
                    self._err(404, "NotFound")
                    return
                self._mp(200, {"data": [{"username": "test_user", "accessLevel": 1}], "done": True, "iterator": None})
                return
            if len(parts) == 1:
                c = COLLS.get(parts[0])
                if c is None or c["owner"] != user:
                    self._err(404, "NotFound")
                    return
                self._mp(200, c["raw"])
                return
            if len(parts) == 2 and parts[1] == "item":
                c = COLLS.get(parts[0])
                if c is None or c["owner"] != user:
                    self._err(404, "NotFound")
                    return
                sq = (qs.get("stoken") or [None])[0]
                if sq is not None and sq == c["cstoken"]:
                    self._mp(200, {"data": [], "done": True, "stoken": c["cstoken"]})
                    return
                self._mp(200, {"data": [v["cur"] for v in c["items"].values()], "done": True, "stoken": c["cstoken"]})
                return
            if len(parts) == 3 and parts[1] == "item":
                c = COLLS.get(parts[0])
                if c is None or c["owner"] != user:
                    self._err(404, "NotFound")
                    return
                it = c["items"].get(parts[2])
                if it is None:
                    self._err(404, "NotFound")
                    return
                self._mp(200, it["cur"])
                return
            if len(parts) == 4 and parts[1] == "item" and parts[3] == "revision":
                c = COLLS.get(parts[0])
                if c is None or c["owner"] != user:
                    self._err(404, "NotFound")
                    return
                it = c["items"].get(parts[2])
                if it is None:
                    self._err(404, "NotFound")
                    return
                # Client expects IteratorListResponse<EncryptedRevision> and
                # rebuilds items via clone_with_revision (online_managers.rs):
                # returning full EncryptedItem dicts breaks deserialization
                # (NULL revisions -> SIGSEGV, rc=-11). Revisions are the
                # stored items' "content" sub-objects, newest-first
                # (test_item_revisions expects [1] == "First draft", i.e.
                # [Second, First]).
                revs = []
                for h in it["hist"]:
                    if isinstance(h, dict) and isinstance(h.get("content"), dict):
                        revs.append(h["content"])
                    else:
                        revs.append(h)
                revs.reverse()
                self._mp(200, {"data": revs, "done": True, "iterator": None})
                return
            if len(parts) == 5 and parts[1] == "item" and parts[3] == "chunk":
                self._send(200, b"chunk")
                return
            self._err(404, "NotFound")
            return
        if path.startswith("/api/v1/invitation/"):
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            rest = path[len("/api/v1/invitation/"):]
            if "fetch_user_profile" in rest:
                # Client uses GET outgoing/fetch_user_profile/?username=
                # (online_managers.rs); must return {"pubkey": bytes}, not
                # the generic invitation list (test_basic_invitations:788
                # fail_if(!user2) on deserialization failure).
                un = (qs.get("username") or [None])[0]
                if isinstance(un, bytes):
                    try:
                        un = un.decode()
                    except Exception:
                        un = None
                if not un:
                    un = "test_user2"
                t = USERS.get(un, USERS["test_user2"])
                self._mp(200, {"pubkey": t["pubkey"]})
                return
            self._mp(200, {"data": [], "done": True, "iterator": None})
            return
        if "member" in path:
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            self._mp(200, {"data": [{"username": "test_user", "accessLevel": 1}], "done": True, "iterator": None})
            return
        self._err(404, "NotFound")
    def do_POST(self):
        import urllib.parse as _up
        u = _up.urlparse(self.path)
        path, qs = u.path, _up.parse_qs(u.query)
        body = self._body()
        if path == "/api/v1/authentication/login_challenge/":
            try:
                req = mp_loads(body) or {}
                username = req.get("username")
            except Exception as e:
                self._err(400, "bad challenge %s" % e)
                return
            usr = USERS.get(username)
            if usr is None:
                self._err(401, "User not found")
                return
            ch = os.urandom(32)
            usr["challenge"] = ch
            self._mp(200, {"challenge": ch, "salt": usr["salt"], "version": CVER})
            return
        if path == "/api/v1/authentication/login/":
            try:
                outer = mp_loads(body) or {}
                rb = bytes(outer.get("response"))
                sg = bytes(outer.get("signature"))
                inner = mp_loads(rb) or {}
                username = inner.get("username")
                ch = bytes(inner.get("challenge"))
            except Exception as e:
                self._err(400, "bad login %s" % e)
                return
            usr = USERS.get(username)
            if usr is None:
                self._err(401, "Unauthorized")
                return
            if usr.get("challenge") is not None and ch != bytes(usr["challenge"]):
                self._err(401, "Unauthorized")
                return
            if not ed_verify(sg, rb, bytes(usr["loginPubkey"])):
                sys.stderr.write("[stub] bad sig %s\n" % username)
                self._err(401, "Unauthorized")
                return
            TSEQ[0] += 1
            tok = "tok-%s-%d" % (username, TSEQ[0])
            usr["token"] = tok
            TOKENS[tok] = username
            self._mp(200, {"token": tok, "user": {"username": usr["username"], "email": usr["email"], "pubkey": usr["pubkey"], "encryptedContent": usr["encryptedContent"]}})
            return
        if path == "/api/v1/authentication/logout/":
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            a = self.headers.get("Authorization") or ""
            TOKENS.pop(a[6:].strip(), None)
            USERS[user]["token"] = None
            self._send(200, b"")
            return
        if path == "/api/v1/test/authentication/reset/":
            try:
                req = mp_loads(body) or {}
                usr2 = req.get("user") or {}
                username = usr2.get("username")
            except Exception as e:
                self._err(400, "bad reset %s" % e)
                return
            if not username or not username.startswith("test_user"):
                self._err(400, "reset test users only")
                return
            USERS[username] = {"username": username, "email": usr2.get("email") or "", "pubkey": bytes(req.get("pubkey") or b""), "encryptedContent": bytes(req.get("encryptedContent") or b""), "loginPubkey": bytes(req.get("loginPubkey") or b""), "salt": bytes(req.get("salt") or b""), "challenge": None, "token": None}
            for k in [k for k, v in COLLS.items() if v["owner"] == username]:
                del COLLS[k]
            self._send(200, b"")
            return
        if path in ("/api/v1/collection/", "/api/v1/collection"):
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            try:
                obj = mp_loads(body) or {}
            except Exception as e:
                self._err(400, "bad coll %s" % e)
                return
            uid = _uid(obj.get("item") or {}) or ("col%d" % (len(COLLS)+1))
            st = _nstok()
            obj["stoken"] = st
            COLLS[uid] = {"owner": user, "raw": obj, "stoken": st, "cstoken": st, "items": {}}
            self._send(200, b"")
            return
        if path == "/api/v1/collection/list_multi/":
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            sq = (qs.get("stoken") or [None])[0]
            mine = [v["raw"] for v in COLLS.values() if v["owner"] == user]
            cur = "cl%d" % len(mine)
            if sq is not None and sq == getattr(self.server, "_llst", None):
                self._mp(200, {"data": [], "done": True, "stoken": sq, "removedMemberships": None})
                return
            self.server._llst = cur
            self._mp(200, {"data": mine, "done": True, "stoken": cur, "removedMemberships": None})
            return
        if path.startswith("/api/v1/collection/"):
            rest = path[len("/api/v1/collection/"):]
            parts = [p for p in rest.split("/") if p]
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            if len(parts) == 3 and parts[1] == "item" and parts[2] in ("batch", "transaction"):
                c = COLLS.get(parts[0])
                if c is None or c["owner"] != user:
                    self._err(404, "NotFound")
                    return
                try:
                    req = mp_loads(body) or {}
                    items = req.get("items") or []
                    deps = req.get("deps")
                except Exception as e:
                    self._err(400, "bad batch %s" % e)
                    return
                txn = (parts[2] == "transaction")
                sq = (qs.get("stoken") or [None])[0]
                col_uid = parts[0]
                # Write stoken (from etebase_collection_get_stoken) guards
                # BOTH batch and transaction: any write carrying a stale
                # collection stoken must 409 (test_collection_transactions:442
                # upload with stoken, test_items_transactions:563-564 item
                # batch+transaction with stoken). Compare against the
                # collection stoken, never the item-list cstoken.
                try:
                    coll_st = (c["raw"].get("stoken") if isinstance(
                        c.get("raw"), dict) else None) or c.get("stoken")
                except Exception:
                    coll_st = c.get("stoken")
                if sq is not None and coll_st is not None and sq != coll_st:
                    self._err(409, "Conflict")
                    return
                # Collection self-updates arrive on this same endpoint
                # (CollectionManager::upload/transaction sends col.item()
                # whose uid == collection uid, see etebase-rs service.rs).
                # They must update c["raw"]["item"], never c["items"],
                # otherwise the collection revision pollutes item list
                # counts (test_simple:212 expects 1, got 2).
                col_updates = [it for it in items
                               if _uid(it) == col_uid]
                user_items = [it for it in items
                              if _uid(it) != col_uid]
                if txn:
                    for it in col_updates:
                        want = _top_etag(it)
                        if want is None:
                            continue
                        try:
                            cur = _cuid((c["raw"].get("item") or {}))
                        except Exception:
                            cur = None
                        if cur is not None and want != cur:
                            self._err(409, "Conflict")
                            return
                    for it in user_items:
                        uid = _uid(it)
                        if uid is None:
                            continue
                        st2 = c["items"].get(uid)
                        if st2 is None:
                            continue
                        # Transaction precondition: client's last-known etag
                        # (top-level "etag", i.e. EncryptedItem::last_etag)
                        # must equal the stored current etag
                        # (content.uid). Comparing content.uid vs
                        # content.uid is always a mismatch after any edit
                        # (B vs A) and wrongly 409s every transaction.
                        want = _top_etag(it)
                        if want is None:
                            continue
                        if want != _cuid(st2["cur"]):
                            self._err(409, "Conflict")
                            return
                if deps:
                    for d in deps:
                        du = d.get("uid")
                        if isinstance(du, bytes):
                            du = du.decode()
                        if du is None:
                            continue
                        de = _norm_str(d.get("etag"))
                        if du == col_uid:
                            # Collection-as-dep (test_collection_as_item block 2):
                            # uid exists as the collection itself. None etag
                            # (fresh col.item() clone, last_etag None) means
                            # no check -> succeed; otherwise compare vs the
                            # collection's current content.uid.
                            if de is None:
                                continue
                            try:
                                cur = _cuid((c["raw"].get("item") or {}))
                            except Exception:
                                cur = None
                            if cur is not None and de != cur:
                                self._err(409, "Conflict")
                                return
                            continue
                        st2 = c["items"].get(du)
                        if st2 is None:
                            # Dep references an item that was never uploaded
                            # (test_collection_as_item block 1 deps=[item2]
                            # new local item): real server 409s even when the
                            # dep etag is None (absent). Skipping here made
                            # the expected-failure transaction succeed
                            # (test_collection_as_item:670).
                            self._err(409, "Conflict")
                            return
                        if de is None:
                            continue
                        if de != _cuid(st2["cur"]):
                            self._err(409, "Conflict")
                            return
                # Collection-as-item mixing rule (test_collection_as_item
                # blocks 1 & 3): CollectionManager::upload/transaction always
                # sends exactly one item (col.item(), uid == collection uid,
                # see etebase service.rs). An item batch/transaction that mixes
                # the collection item with regular items is rejected by the
                # real server. Single-col_item writes still take the
                # col_update path below (test_simple collection flows).
                if col_updates and user_items:
                    self._err(409, "Conflict")
                    return
                for it in col_updates:
                    try:
                        c["raw"]["item"] = it
                    except Exception:
                        pass
                for it in user_items:
                    uid = _uid(it)
                    if uid is None:
                        continue
                    if uid in c["items"]:
                        c["items"][uid]["cur"] = it
                        c["items"][uid]["hist"].append(it)
                    else:
                        c["items"][uid] = {"cur": it, "hist": [it]}
                # Any state change bumps the collection stoken (real server
                # does: item writes invalidate cached collection stoken, so
                # a stale write stoken 409s). Item-list cstoken only moves
                # on user-item changes (list/fetch_updates namespace).
                if col_updates or user_items:
                    nst = _nstok()
                    c["stoken"] = nst
                    try:
                        c["raw"]["stoken"] = nst
                    except Exception:
                        pass
                if user_items:
                    c["cstoken"] = _nstok()
                self._send(200, b"")
                return
            if len(parts) == 3 and parts[1] == "item" and parts[2] == "fetch_updates":
                c = COLLS.get(parts[0])
                if c is None or c["owner"] != user:
                    self._err(404, "NotFound")
                    return
                self._mp(200, {"data": [v["cur"] for v in c["items"].values()], "done": True, "stoken": c["cstoken"]})
                return
            if "invite" in rest or "member" in rest or "chunk" in rest:
                self._send(200, b"")
                return
            self._err(404, "NotFound")
            return
        if path.startswith("/api/v1/invitation/"):
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            rest = path[len("/api/v1/invitation/"):]
            # invite POSTs SignedInvitation to outgoing/ and only checks HTTP
            # status (online_managers.rs invite()); returning a UserProfile
            # body here is wrong, so only fetch_user_profile answers pubkey.
            if "fetch_user_profile" in rest:
                try:
                    req = mp_loads(body) if body else {}
                except Exception:
                    req = {}
                un = (qs.get("username") or [None])[0]
                if isinstance(req, dict) and req.get("username"):
                    un = req.get("username")
                if not un:
                    un = "test_user2"
                t = USERS.get(un, USERS["test_user2"])
                self._mp(200, {"pubkey": t["pubkey"]})
                return
            self._send(200, b"")
            return
        if "member" in path:
            user = self._user()
            if user is None:
                self._err(401, "Unauthorized")
                return
            self._mp(200, {"data": [{"username": "test_user", "accessLevel": 1}], "done": True, "iterator": None})
            return
        self._err(404, "NotFound")
    def do_PUT(self):
        if "chunk" in self.path:
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
            if self._user() is None:
                self._err(401, "Unauthorized")
                return
            self._send(200, b"")
            return
        self._err(404, "NotFound")
    def do_PATCH(self):
        self._err(404, "NotFound")
    def do_DELETE(self):
        self._err(404, "NotFound")

def run(port=8033):
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    sys.stderr.write("[stub] listen 127.0.0.1:%d\n" % port)
    sys.stderr.flush()
    srv.serve_forever()

if __name__ == "__main__":
    run(int(sys.argv[1]) if len(sys.argv) > 1 else 8033)
