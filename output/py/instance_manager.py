#!/usr/bin/env python3
"""Manage Incus instances through the Incus REST API.

Only the Python standard library is used. By default the local Unix socket is
used; remote servers are reachable over HTTPS with a client certificate.

Examples:
  python incus_manager_api.py list
  python incus_manager_api.py show web01
  python incus_manager_api.py create web01 images:debian/12 --start
  python incus_manager_api.py update web01 --config limits.cpu=2 --config limits.memory=4GiB
  python incus_manager_api.py start web01
  python incus_manager_api.py exec web01 -- uname -a
  python incus_manager_api.py snapshot create web01 before-upgrade
  python incus_manager_api.py backup web01 --output ./backups/web01.tar.gz

Remote server:
  python incus_manager_api.py --url https://incus.example.com:8443 \\
      --cert ~/.config/incus/client.crt --key ~/.config/incus/client.key \\
      --server-cert ./server.crt list

Socket lookup order: --socket, $INCUS_SOCKET, $INCUS_DIR/unix.socket,
/var/lib/incus/unix.socket, /run/incus/unix.socket.

`exec` is non-interactive (output isrecorded and printed after the command finishes)
and an interactive `console` is not available, because both need websocket streaming.
`console --show-log` works.
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
import shutil
import socket
import ssl
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlparse

try:  # optional, only used for YAML output
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


class IncusError(RuntimeError):
    pass


# Image servers that the CLI knows by default.
REMOTES = {
    "images": "https://images.linuxcontainers.org",
    "ubuntu": "https://cloud-images.ubuntu.com/releases",
    "ubuntu-daily": "https://cloud-images.ubuntu.com/daily",
}


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path: str, timeout: float | None = None) -> None:
        super().__init__("localhost", timeout=timeout)
        self.unix_path = path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if self.timeout is not None:
            sock.settimeout(self.timeout)
        sock.connect(self.unix_path)
        self.sock = sock


class IncusClient:
    def __init__(self, *, socket_path: str | None = None, url: str | None = None,
                 cert: str | None = None, key: str | None = None,
                 server_cert: str | None = None, insecure: bool = False,
                 project: str | None = None) -> None:
        self.project = project
        self.url = url
        self.ssl_context: ssl.SSLContext | None = None
        self.socket_path: str | None = None

        if url:
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise IncusError("--url must look like https://host[:8443]")
            self.host = parsed.hostname
            self.port = parsed.port or 8443
            ctx = ssl.create_default_context(cafile=server_cert) if server_cert \
                else ssl.create_default_context()
            if insecure:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            cfg = Path(os.environ.get("INCUS_CONF", "~/.config/incus")).expanduser()
            cert = cert or str(cfg / "client.crt")
            key = key or str(cfg / "client.key")
            try:
                ctx.load_cert_chain(cert, key)
            except (OSError, ssl.SSLError) as exc:
                raise IncusError(f"Cannot load client certificate/key: {exc}") from exc
            self.ssl_context = ctx
        else:
            self.socket_path = self._find_socket(socket_path)

    @staticmethod
    def _find_socket(explicit: str | None) -> str:
        candidates = []
        if explicit:
            candidates.append(explicit)
        if os.environ.get("INCUS_SOCKET"):
            candidates.append(os.environ["INCUS_SOCKET"])
        if os.environ.get("INCUS_DIR"):
            candidates.append(os.path.join(os.environ["INCUS_DIR"], "unix.socket"))
        candidates += ["/var/lib/incus/unix.socket", "/run/incus/unix.socket"]
        for path in candidates:
            if os.path.exists(path):
                return path
        raise IncusError("No Incus socket found. Tried: " + ", ".join(candidates))

    # ---- low level -------------------------------------------------------

    def _connection(self) -> http.client.HTTPConnection:
        if self.url:
            return http.client.HTTPSConnection(self.host, self.port,
                                               context=self.ssl_context)
        return UnixHTTPConnection(self.socket_path)  # type: ignore[arg-type]

    def _send(self, method: str, path: str, params: dict[str, Any] | None,
              body: Any, headers: dict[str, str] | None):
        query = dict(params or {})
        if self.project:
            query.setdefault("project", self.project)
        target = path + ("?" + urlencode(query) if query else "")
        hdrs = dict(headers or {})
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        conn = self._connection()
        try:
            conn.request(method, target, body=data, headers=hdrs)
            return conn, conn.getresponse()
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            conn.close()
            raise IncusError(f"Cannot reach Incus: {exc}") from exc

    def request(self, method: str, path: str, *, params: dict[str, Any] | None = None,
                body: Any = None, headers: dict[str, str] | None = None):
        """Return (decoded JSON envelope, response headers)."""
        conn, resp = self._send(method, path, params, body, headers)
        try:
            raw = resp.read()
            resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        finally:
            conn.close()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            raise IncusError(f"{method} {path}: HTTP {resp.status}, non-JSON reply")
        if payload.get("type") == "error" or resp.status >= 400:
            raise IncusError(f"{method} {path}: {payload.get('error', resp.reason)} "
                             f"(code {payload.get('error_code', resp.status)})")
        return payload, resp_headers

    def fetch_raw(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        conn, resp = self._send("GET", path, params, None, None)
        try:
            raw = resp.read()
        finally:
            conn.close()
        if resp.status >= 400:
            raise IncusError(f"GET {path}: HTTP {resp.status} {raw[:200]!r}")
        return raw

    def download(self, path: str, dest: Path) -> None:
        conn, resp = self._send("GET", path, None, None, None)
        try:
            if resp.status >= 400:
                raise IncusError(f"GET {path}: HTTP {resp.status} {resp.read()[:200]!r}")
            with open(dest, "wb") as fh:
                shutil.copyfileobj(resp, fh)
        finally:
            conn.close()

    # ---- helpers ---------------------------------------------------------

    def get(self, path: str, **params: Any) -> Any:
        payload, _ = self.request("GET", path, params=params)
        return payload["metadata"]

    def wait(self, operation_id: str) -> dict[str, Any]:
        payload, _ = self.request("GET", f"/1.0/operations/{operation_id}/wait",
                                  params={"timeout": -1})
        op = payload["metadata"]
        if op.get("status_code") != 200:
            raise IncusError(op.get("err") or f"Operation failed: {op.get('status')}")
        return op

    def run(self, method: str, path: str, *, params: dict[str, Any] | None = None,
            body: Any = None, headers: dict[str, str] | None = None) -> Any:
        """Send a modifying request; wait for it if it returned an operation."""
        payload, _ = self.request(method, path, params=params, body=body, headers=headers)
        if payload.get("type") == "async":
            return self.wait(payload["metadata"]["id"])
        return payload.get("metadata")


# ---- output helpers -------------------------------------------------------

def dump(data: Any, fmt: str = "json") -> None:
    if fmt == "yaml" and yaml is not None:
        print(yaml.safe_dump(data, sort_keys=True), end="")
    else:
        print(json.dumps(data, indent=2, sort_keys=True))


def print_table(headers: list[str], rows: list[list[str]], csv: bool = False) -> None:
    if csv:
        for row in rows:
            print(",".join(row))
        return
    widths = [max(len(h), *(len(r[i]) for r in rows)) if rows else len(h)
              for i, h in enumerate(headers)]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    fmt = "| " + " | ".join(f"{{:<{w}}}" for w in widths) + " |"
    print(line)
    print(fmt.format(*headers))
    print(line)
    for row in rows:
        print(fmt.format(*row))
    if rows:
        print(line)


def addresses(state: dict[str, Any] | None, family: str) -> str:
    out = []
    for name, nic in ((state or {}).get("network") or {}).items():
        if name == "lo":
            continue
        for addr in nic.get("addresses", []):
            if addr["family"] == family and addr.get("scope") == "global":
                out.append(f"{addr['address']} ({name})")
    return "\n".join(out)


def parse_pairs(items: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for item in items:
        if "=" not in item:
            raise IncusError(f"Expected KEY=VALUE, got: {item!r}")
        key, value = item.split("=", 1)
        if not key:
            raise IncusError(f"Empty key in: {item!r}")
        pairs.append((key, value))
    return pairs


def parse_source(source: str) -> dict[str, Any]:
    if ":" in source:
        remote, alias = source.split(":", 1)
        if remote == "local":
            source = alias
        elif remote in REMOTES:
            return {"type": "image", "mode": "pull", "protocol": "simplestreams",
                    "server": REMOTES[remote], "alias": alias}
        else:
            raise IncusError(f"Unsupported image remote {remote!r}. "
                             f"Known remotes: local, {', '.join(REMOTES)}")
    if len(source) == 64 and all(c in "0123456789abcdef" for c in source):
        return {"type": "image", "fingerprint": source}
    return {"type": "image", "alias": source}


def ipath(name: str, *parts: str) -> str:
    return "/1.0/instances/" + quote(name, safe="") + "".join("/" + quote(p, safe="") for p in parts)


# ---- actions ---------------------------------------------------------------

def cmd_list(c: IncusClient, args) -> None:
    items = c.get("/1.0/instances", recursion=2)
    if args.format in ("json", "yaml"):
        dump(items, args.format)
        return
    rows = [[i["name"], i["status"].upper(), addresses(i.get("state"), "inet"),
             addresses(i.get("state"), "inet6"),
             "VIRTUAL-MACHINE" if i["type"] == "virtual-machine" else "CONTAINER",
             str(len(i.get("snapshots") or []))] for i in items]
    print_table(["NAME", "STATE", "IPV4", "IPV6", "TYPE", "SNAPSHOTS"], rows,
                csv=args.format == "csv")


def cmd_show(c: IncusClient, args) -> None:
    dump(c.get(ipath(args.instance), recursion=1), "yaml")


def set_state(c: IncusClient, name: str, action: str, *, force: bool = False,
              timeout: int = 30, stateful: bool = False) -> None:
    c.run("PUT", ipath(name, "state"),
          body={"action": action, "force": force, "timeout": timeout,
                "stateful": stateful})


def cmd_create(c: IncusClient, args) -> None:
    devices = {}
    for device in args.device:
        fields = device.split(",")
        if len(fields) < 2:
            raise IncusError("Device syntax is NAME,TYPE[,KEY=VALUE...].")
        name, kind, *props = fields
        devices[name] = {"type": kind, **dict(parse_pairs(props))}
    body: dict[str, Any] = {
        "name": args.instance,
        "source": parse_source(args.source),
        "type": "virtual-machine" if args.vm else "container",
        "config": dict(parse_pairs(args.config)),
        "devices": devices,
    }
    if args.profiles:
        body["profiles"] = args.profiles
    c.run("POST", "/1.0/instances", body=body)
    print(f"Created {args.instance}")
    if args.start:
        set_state(c, args.instance, "start")
        print(f"Started {args.instance}")


WRITABLE = ("architecture", "config", "description", "devices", "ephemeral",
            "profiles", "stateful")


def cmd_update(c: IncusClient, args) -> None:
    if not (args.config or args.unset_config or args.device or args.description is not None):
        raise IncusError("Specify at least one --config, --unset-config, --device or --description.")
    payload, headers = c.request("GET", ipath(args.instance))
    meta = payload["metadata"]
    body = {k: meta[k] for k in WRITABLE if k in meta}
    body.setdefault("config", {})
    body.setdefault("devices", {})

    for key, value in parse_pairs(args.config):
        body["config"][key] = value
    for key in args.unset_config:
        body["config"].pop(key, None)
    for device in args.device:
        name, *props = device.split(",")
        if not props:
            raise IncusError("Device update syntax is NAME,KEY=VALUE[,KEY=VALUE...].")
        if name not in body["devices"]:
            raise IncusError(f"Device {name!r} is not defined directly on {args.instance}.")
        body["devices"][name].update(parse_pairs(props))
    if args.description is not None:
        body["description"] = args.description

    # If-Match makes the update fail rather than overwrite concurrent changes.
    hdrs = {"If-Match": headers["etag"]} if "etag" in headers else None
    c.run("PUT", ipath(args.instance), body=body, headers=hdrs)
    print(f"Updated {args.instance}")


def cmd_delete(c: IncusClient, args) -> None:
    if args.force:
        status = c.get(ipath(args.instance)).get("status")
        if status and status.lower() != "stopped":
            set_state(c, args.instance, "stop", force=True)
    c.run("DELETE", ipath(args.instance))
    print(f"Deleted {args.instance}")


def cmd_power(c: IncusClient, args) -> None:
    set_state(c, args.instance, args.action,
              force=getattr(args, "force", False),
              timeout=getattr(args, "timeout", 30))
    print(f"{args.action.capitalize()} {args.instance}: done")


def cmd_console(c: IncusClient, args) -> int:
    if not args.show_log:
        raise IncusError("Interactive console needs websockets, which this script does "
                         "not implement. Use --show-log, or run `incus console`.")
    sys.stdout.write(c.fetch_raw(ipath(args.instance, "console")).decode(errors="replace"))
    return 0


def cmd_exec(c: IncusClient, args) -> int:
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise IncusError("Provide a command, e.g. exec web01 -- uname -a")
    op = c.run("POST", ipath(args.instance, "exec"), body={
        "command": command,
        "environment": {},
        "interactive": False,
        "wait-for-websocket": False,
        "record-output": True,
    })
    result = op.get("metadata") or {}
    for fd, stream in (("1", sys.stdout), ("2", sys.stderr)):
        log_path = (result.get("output") or {}).get(fd)
        if not log_path:
            continue
        stream.write(c.fetch_raw(log_path).decode(errors="replace"))
        stream.flush()
        try:  # the server keeps recorded output until it is deleted
            c.run("DELETE", log_path)
        except IncusError:
            pass
    return int(result.get("return", 0))


def cmd_snapshot(c: IncusClient, args) -> None:
    sa = args.snapshot_action
    if sa == "list":
        snaps = c.get(ipath(args.instance, "snapshots"), recursion=1)
        rows = [[s["name"].split("/")[-1], s.get("created_at", ""),
                 "YES" if s.get("stateful") else "NO"] for s in snaps]
        print_table(["NAME", "TAKEN AT", "STATEFUL"], rows)
    elif sa == "create":
        c.run("POST", ipath(args.instance, "snapshots"),
              body={"name": args.snapshot, "stateful": args.stateful})
        print(f"Snapshot {args.snapshot} created")
    elif sa == "restore":
        c.run("PUT", ipath(args.instance),
              body={"restore": args.snapshot, "stateful": args.stateful})
        print(f"Restored {args.instance} from {args.snapshot}")
    elif sa == "delete":
        c.run("DELETE", ipath(args.instance, "snapshots", args.snapshot))
        print(f"Snapshot {args.snapshot} deleted")


def cmd_backup(c: IncusClient, args) -> None:
    destination = Path(args.output).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    name = f"backup-{int(time.time())}"
    c.run("POST", ipath(args.instance, "backups"), body={
        "name": name,
        "instance_only": args.instance_only,
        "optimized_storage": args.optimized_storage,
    })
    try:
        c.download(ipath(args.instance, "backups", name, "export"), destination)
    finally:  # the server-side copy is only a staging area
        try:
            c.run("DELETE", ipath(args.instance, "backups", name))
        except IncusError as exc:
            print(f"warning: could not remove server-side backup {name}: {exc}",
                  file=sys.stderr)
    print(f"Backup written to {destination}")


# ---- CLI -------------------------------------------------------------------

def add_project(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", help="Incus project name")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Incus instances through the REST API.")
    conn = parser.add_argument_group("connection")
    conn.add_argument("--socket", help="Path to the Incus Unix socket")
    conn.add_argument("--url", help="HTTPS endpoint, e.g. https://host:8443")
    conn.add_argument("--cert", help="Client certificate (default: ~/.config/incus/client.crt)")
    conn.add_argument("--key", help="Client key (default: ~/.config/incus/client.key)")
    conn.add_argument("--server-cert", help="Server certificate / CA to trust")
    conn.add_argument("--insecure", action="store_true", help="Do not verify the server certificate")

    sub = parser.add_subparsers(dest="action", required=True)

    p = sub.add_parser("list", help="List instances")
    add_project(p)
    p.add_argument("--format", choices=("table", "json", "yaml", "csv"), default="table")

    p = sub.add_parser("show", help="Show instance configuration (expanded)")
    add_project(p)
    p.add_argument("instance")

    p = sub.add_parser("create", help="Create an instance from an image")
    add_project(p)
    p.add_argument("instance")
    p.add_argument("source", help="e.g. images:debian/12 or a local image alias")
    p.add_argument("--vm", action="store_true", help="Create a virtual machine")
    p.add_argument("--start", action="store_true", help="Start after creation")
    p.add_argument("--profile", action="append", dest="profiles", help="Profile; repeatable")
    p.add_argument("--config", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--device", action="append", default=[], metavar="NAME,TYPE,KEY=VALUE,...")

    p = sub.add_parser("update", help="Update instance config and/or device properties")
    add_project(p)
    p.add_argument("instance")
    p.add_argument("--config", action="append", default=[], metavar="KEY=VALUE")
    p.add_argument("--unset-config", action="append", default=[], metavar="KEY")
    p.add_argument("--device", action="append", default=[], metavar="NAME,KEY=VALUE,...")
    p.add_argument("--description")

    p = sub.add_parser("delete", help="Delete an instance (destructive)")
    add_project(p)
    p.add_argument("instance")
    p.add_argument("--force", action="store_true", help="Force stop before deletion")

    for action in ("start", "stop", "restart"):
        p = sub.add_parser(action, help=f"{action.capitalize()} an instance")
        add_project(p)
        p.add_argument("instance")
        if action in ("stop", "restart"):
            p.add_argument("--force", action="store_true", help="Force stop")
        if action == "stop":
            p.add_argument("--timeout", type=int, default=30,
                           help="Graceful shutdown timeout in seconds (default: 30)")

    p = sub.add_parser("console", help="Show the instance console log")
    add_project(p)
    p.add_argument("instance")
    p.add_argument("--show-log", action="store_true", help="Print the console log")

    p = sub.add_parser("exec", help="Run a command inside an instance (non-interactive)")
    add_project(p)
    p.add_argument("instance")
    p.add_argument("command", nargs=argparse.REMAINDER, help="Command after --")

    snap = sub.add_parser("snapshot", help="Manage instance snapshots")
    snap_sub = snap.add_subparsers(dest="snapshot_action", required=True)
    for action in ("list", "create", "restore", "delete"):
        p = snap_sub.add_parser(action)
        add_project(p)
        p.add_argument("instance")
        if action != "list":
            p.add_argument("snapshot")
        if action in ("create", "restore"):
            p.add_argument("--stateful", action="store_true",
                           help="Include / restore runtime state where supported")

    p = sub.add_parser("backup", help="Export an instance to a backup archive")
    add_project(p)
    p.add_argument("instance")
    p.add_argument("--output", required=True, help="Destination archive path")
    p.add_argument("--instance-only", action="store_true", help="Exclude snapshots")
    p.add_argument("--optimized-storage", action="store_true",
                   help="Use storage-driver-specific optimized format")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        client = IncusClient(socket_path=args.socket, url=args.url, cert=args.cert,
                             key=args.key, server_cert=args.server_cert,
                             insecure=args.insecure,
                             project=getattr(args, "project", None))
        action = args.action
        if action == "list":
            cmd_list(client, args)
        elif action == "show":
            cmd_show(client, args)
        elif action == "create":
            cmd_create(client, args)
        elif action == "update":
            cmd_update(client, args)
        elif action == "delete":
            cmd_delete(client, args)
        elif action in ("start", "stop", "restart"):
            cmd_power(client, args)
        elif action == "console":
            return cmd_console(client, args)
        elif action == "exec":
            return cmd_exec(client, args)
        elif action == "snapshot":
            cmd_snapshot(client, args)
        elif action == "backup":
            cmd_backup(client, args)
        return 0
    except IncusError as exc:
        print(f"incus-manager: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
