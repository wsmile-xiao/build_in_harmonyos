#!/usr/bin/env python3
"""Consumer test for the pgcopydb Conan package.

The installed ``pgcopydb`` binary is exercised against two *real* PostgreSQL
18.3 instances that are created with the binaries of the ``postgresql``
dependency package (initdb + postgres), exactly the way the tool is meant to be
used.

Usage:

    pgcopydb_test.py <postgres-prefix> <pgcopydb-binary> <workdir>

Exit code is 0 only when every assertion passes.
"""
import os
import shutil
import signal
import struct
import subprocess
import sys
import time

PG_PREFIX = os.path.abspath(sys.argv[1])
PGCOPYDB = os.path.abspath(sys.argv[2])
WORKDIR = os.path.abspath(sys.argv[3])

PG_BIN = os.path.join(PG_PREFIX, "bin")
PG_LIB = os.path.join(PG_PREFIX, "lib")

results = []


def report(name, ok, detail=""):
    results.append((name, ok))
    print("%-4s %s%s" % ("PASS" if ok else "FAIL", name,
                         (" — " + detail) if detail else ""), flush=True)


def env_for_pg():
    env = os.environ.copy()
    env["PATH"] = PG_BIN + os.pathsep + env.get("PATH", "")
    libpath = [PG_LIB, os.path.join(PG_LIB, "postgresql")]
    if env.get("LD_LIBRARY_PATH"):
        libpath.append(env["LD_LIBRARY_PATH"])
    env["LD_LIBRARY_PATH"] = os.pathsep.join(libpath)
    env.pop("POSIXLY_CORRECT", None)
    return env


ENV = env_for_pg()


def run(cmd, env=None, timeout=600, check=False):
    proc = subprocess.run(cmd, env=env or ENV, capture_output=True, text=True,
                          timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError("command failed: %s\n%s\n%s"
                           % (" ".join(cmd), proc.stdout, proc.stderr))
    return proc


# --------------------------------------------------------------------------
# Minimal ELF reader (no readelf/nm dependency)
# --------------------------------------------------------------------------
class Elf:
    def __init__(self, path):
        with open(path, "rb") as handle:
            self.raw = handle.read()
        self.is_elf = self.raw[:4] == b"\x7fELF"
        self.elf_class = self.raw[4]
        self.elf_data = self.raw[5]
        (self.e_machine,) = struct.unpack_from("<H", self.raw, 18)
        (self.e_shoff,) = struct.unpack_from("<Q", self.raw, 0x28)
        (self.e_shentsize,) = struct.unpack_from("<H", self.raw, 0x3A)
        (self.e_shnum,) = struct.unpack_from("<H", self.raw, 0x3C)
        (self.e_shstrndx,) = struct.unpack_from("<H", self.raw, 0x3E)

    def sections(self):
        out = []
        for index in range(self.e_shnum):
            off = self.e_shoff + index * self.e_shentsize
            name, stype, flags, addr, offset, size, link, info, align, entsize = \
                struct.unpack_from("<IIQQQQIIQQ", self.raw, off)
            out.append({"name_off": name, "type": stype, "addr": addr,
                        "offset": offset, "size": size, "link": link,
                        "entsize": entsize})
        return out

    def section_names(self):
        sections = self.sections()
        strtab = sections[self.e_shstrndx]
        base = strtab["offset"]
        names = []
        for section in sections:
            start = base + section["name_off"]
            end = self.raw.index(b"\x00", start)
            names.append(self.raw[start:end].decode("utf-8", "replace"))
        return names

    def _cstr(self, offset):
        end = self.raw.index(b"\x00", offset)
        return self.raw[offset:end].decode("utf-8", "replace")

    def _dyn_strings(self):
        sections = self.sections()
        names = self.section_names()
        for section, name in zip(sections, names):
            if name == ".dynstr":
                return section["offset"]
        return None

    def dynamic_entries(self):
        """Yield (tag, value) of the .dynamic section."""
        sections = self.sections()
        names = self.section_names()
        for section, name in zip(sections, names):
            if name != ".dynamic":
                continue
            count = section["size"] // 16
            for index in range(count):
                tag, val = struct.unpack_from(
                    "<QQ", self.raw, section["offset"] + index * 16)
                yield tag, val

    def needed(self):
        strtab = self._dyn_strings()
        out = []
        for tag, val in self.dynamic_entries():
            if tag == 1 and strtab is not None:      # DT_NEEDED
                out.append(self._cstr(strtab + val))
        return out

    def runpath(self):
        strtab = self._dyn_strings()
        out = []
        for tag, val in self.dynamic_entries():
            if tag in (15, 29) and strtab is not None:   # DT_RPATH / DT_RUNPATH
                out.append(self._cstr(strtab + val))
        return out

    def undefined_symbols(self):
        sections = self.sections()
        names = self.section_names()
        out = set()
        for section, name in zip(sections, names):
            if section["type"] != 11:                # SHT_DYNSYM
                continue
            strtab_section = sections[section["link"]]
            strtab = strtab_section["offset"]
            entsize = section["entsize"] or 24
            count = section["size"] // entsize
            for index in range(count):
                off = section["offset"] + index * entsize
                st_name, st_info, st_other, st_shndx, st_value, st_size = \
                    struct.unpack_from("<IBBHQQ", self.raw, off)
                if st_shndx == 0 and st_name:        # SHN_UNDEF
                    out.add(self._cstr(strtab + st_name))
        return out


# --------------------------------------------------------------------------
# PostgreSQL instances
# --------------------------------------------------------------------------
class Cluster:
    def __init__(self, root, name, port):
        self.name = name
        self.port = port
        self.datadir = os.path.join(root, name)
        self.logfile = os.path.join(root, "%s.log" % name)
        self.proc = None

    def initdb(self):
        os.makedirs(self.datadir, exist_ok=True)
        run([os.path.join(PG_BIN, "initdb"), "--no-sync", "-U", "postgres",
             "-D", self.datadir], check=True)
        # OHOS cannot bind Unix domain sockets: use TCP loopback only.
        with open(os.path.join(self.datadir, "postgresql.conf"), "a") as handle:
            handle.write(
                "listen_addresses = '127.0.0.1'\n"
                "unix_socket_directories = ''\n"
                "port = %d\n"
                "fsync = off\n"
                "full_page_writes = off\n" % self.port)

    def start(self):
        log = open(self.logfile, "wb")
        self.proc = subprocess.Popen(
            [os.path.join(PG_BIN, "postgres"), "-D", self.datadir,
             "-p", str(self.port)],
            env=ENV, stdout=log, stderr=log)
        deadline = time.time() + 60
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError("%s exited early:\n%s"
                                   % (self.name, open(self.logfile).read()))
            probe = run([os.path.join(PG_BIN, "pg_isready"), "-h", "127.0.0.1",
                         "-p", str(self.port), "-U", "postgres", "-q"])
            if probe.returncode == 0:
                return
            time.sleep(0.5)
        raise RuntimeError("%s did not become ready" % self.name)

    def stop(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGINT)
            try:
                self.proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=30)

    @property
    def uri(self):
        return "postgres://postgres@127.0.0.1:%d/postgres" % self.port


def psql(cluster, sql, db="postgres", extra=None):
    cmd = [os.path.join(PG_BIN, "psql"), "-h", "127.0.0.1", "-p",
           str(cluster.port), "-U", "postgres", "-d", db, "-tAX",
           "-v", "ON_ERROR_STOP=1"]
    cmd += (extra or [])
    cmd += ["-c", sql]
    return run(cmd, check=True)


def free_port():
    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


FIXTURE = """
CREATE SCHEMA app;
CREATE TABLE app.customers (
    id serial PRIMARY KEY,
    name text NOT NULL,
    email text UNIQUE,
    created_at timestamptz DEFAULT now()
);
CREATE TABLE app.orders (
    id bigserial PRIMARY KEY,
    customer_id int REFERENCES app.customers(id),
    amount numeric(10,2),
    notes text
);
CREATE INDEX orders_customer_idx ON app.orders(customer_id);
CREATE VIEW app.recent_orders AS SELECT * FROM app.orders WHERE amount > 100;
CREATE SEQUENCE app.custom_seq START 1000;
INSERT INTO app.customers (name, email)
    SELECT 'customer ' || g, 'c' || g || '@example.com'
    FROM generate_series(1, 500) g;
INSERT INTO app.orders (customer_id, amount, notes)
    SELECT (g % 500) + 1, (g % 1000) / 10.0, 'order ' || g
    FROM generate_series(1, 2000) g;
"""


def main():
    os.makedirs(WORKDIR, exist_ok=True)
    root = os.path.join(WORKDIR, "pgcopydb-test")
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)

    # ---- binary level assertions -----------------------------------------
    version = run([PGCOPYDB, "--version"])
    report("C1 pgcopydb --version reports 0.18",
           version.returncode == 0 and "0.18" in version.stdout,
           version.stdout.strip().splitlines()[0] if version.stdout else
           version.stderr.strip())

    helpout = run([PGCOPYDB, "--help"])
    # pgcopydb prints the command tree on stderr (commandline_print_usage).
    helptext = helpout.stdout + helpout.stderr
    expected_commands = ("clone", "fork", "follow", "snapshot", "compare",
                         "copy", "dump", "restore", "list", "stream", "ping")
    missing = [c for c in expected_commands if c not in helptext]
    report("C2 pgcopydb --help lists every sub-command",
           helpout.returncode == 0 and not missing,
           "missing=%s" % missing if missing else "")

    elf = Elf(PGCOPYDB)
    report("H1 artifact is an ELF64 little-endian AArch64 executable",
           elf.is_elf and elf.elf_class == 2 and elf.elf_data == 1 and
           elf.e_machine == 0xB7,
           "class=%d data=%d machine=0x%x" % (elf.elf_class, elf.elf_data,
                                              elf.e_machine))

    report("H2 artifact loads against the musl dynamic loader",
           b"ld-musl-aarch64.so.1" in elf.raw)

    sysv = {"semget", "semctl", "semop", "semtimedop", "msgget", "msgsnd",
            "msgrcv", "msgctl", "shmget", "shmat", "shmctl"}
    undefined = elf.undefined_symbols()
    leftover = sorted(sysv & undefined)
    report("H3 no System V IPC symbol is referenced at run time",
           not leftover, "leftover=%s" % leftover if leftover else "")

    section_names = elf.section_names()
    report("P1 artifact carries the HarmonyOS PC .codesign section",
           ".codesign" in section_names)

    needed = elf.needed()
    report("P2 DT_NEEDED limited to libpq.so.5 and libc.so",
           sorted(needed) == ["libc.so", "libpq.so.5"], "needed=%s" % needed)

    # ---- two real PostgreSQL instances -----------------------------------
    source = Cluster(root, "source", free_port())
    target = Cluster(root, "target", free_port())
    try:
        source.initdb()
        target.initdb()
        source.start()
        target.start()
        report("C3 source and target PostgreSQL 18.3 instances are up", True)

        ping = run([PGCOPYDB, "ping", "--source", source.uri,
                    "--target", target.uri])
        report("C4 pgcopydb ping connects to both instances",
               ping.returncode == 0,
               ping.stderr.strip().splitlines()[-1] if ping.returncode else "")

        psql(source, FIXTURE)
        report("C5 fixture loaded into the source database", True)

        clonepath = os.path.join(root, "clone")
        clone = run([PGCOPYDB, "clone", "--source", source.uri,
                     "--target", target.uri, "--dir", clonepath])
        report("C6 pgcopydb clone completes",
               clone.returncode == 0,
               clone.stderr.strip().splitlines()[-1] if clone.returncode else "")

        source_counts = psql(source, "SELECT (SELECT count(*) FROM app.customers)"
                                     " || '/' || (SELECT count(*) FROM app.orders)"
                                     " || '/' || (SELECT sum(amount) FROM app.orders)").stdout.strip()
        target_counts = psql(target, "SELECT (SELECT count(*) FROM app.customers)"
                                     " || '/' || (SELECT count(*) FROM app.orders)"
                                     " || '/' || (SELECT sum(amount) FROM app.orders)").stdout.strip()
        report("C7 target rows match the source (count/sum)",
               source_counts == target_counts and source_counts,
               "source=%s target=%s" % (source_counts, target_counts))

        source_objects = psql(source, "SELECT string_agg(kind || ':' || name, ',' ORDER BY kind, name)"
                              " FROM (SELECT 'table' kind, tablename name FROM pg_tables WHERE schemaname='app'"
                              " UNION ALL SELECT 'index', indexname FROM pg_indexes WHERE schemaname='app'"
                              " UNION ALL SELECT 'sequence', sequence_name FROM information_schema.sequences WHERE sequence_schema='app') s").stdout.strip()
        target_objects = psql(target, "SELECT string_agg(kind || ':' || name, ',' ORDER BY kind, name)"
                              " FROM (SELECT 'table' kind, tablename name FROM pg_tables WHERE schemaname='app'"
                              " UNION ALL SELECT 'index', indexname FROM pg_indexes WHERE schemaname='app'"
                              " UNION ALL SELECT 'sequence', sequence_name FROM information_schema.sequences WHERE sequence_schema='app') s").stdout.strip()
        report("C8 schema objects (tables/indexes/sequences) copied",
               source_objects == target_objects and bool(source_objects),
               "source=%s target=%s" % (source_objects, target_objects))

        cmpdir = os.path.join(root, "compare")
        schema_cmp = run([PGCOPYDB, "compare", "schema", "--source", source.uri,
                          "--target", target.uri, "--dir", cmpdir])
        report("C9 pgcopydb compare schema reports no difference",
               schema_cmp.returncode == 0,
               schema_cmp.stderr.strip().splitlines()[-1] if schema_cmp.returncode else "")

        data_cmp = run([PGCOPYDB, "compare", "data", "--source", source.uri,
                        "--target", target.uri, "--dir", cmpdir])
        report("C10 pgcopydb compare data reports identical checksums",
               data_cmp.returncode == 0,
               data_cmp.stderr.strip().splitlines()[-1] if data_cmp.returncode else "")

        # A second, independent clone run into a fresh database proves the
        # SysV IPC replacements are stable across repeated process trees (each
        # run creates semaphores, queues and forks its own workers).
        psql(target, "CREATE DATABASE clone_again")
        second_target = target.uri.rsplit("/", 1)[0] + "/clone_again"
        second = run([PGCOPYDB, "clone", "--source", source.uri,
                      "--target", second_target, "--dir",
                      os.path.join(root, "clone2")])
        again = psql(target, "SELECT (SELECT count(*) FROM app.customers) || '/'"
                             " || (SELECT count(*) FROM app.orders)",
                     db="clone_again").stdout.strip() if second.returncode == 0 else ""
        report("C11 a repeated clone run into a fresh database succeeds",
               second.returncode == 0 and again == "500/2000",
               "rc=%d rows=%s" % (second.returncode, again))
    finally:
        source.stop()
        target.stop()

    failed = [name for name, ok in results if not ok]
    print("\n%d/%d assertions passed" % (len(results) - len(failed), len(results)))
    if failed:
        print("failed: %s" % ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
