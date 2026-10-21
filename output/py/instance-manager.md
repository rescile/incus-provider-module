The instance manager for Incus allows to manage workloads through a REST API. It connects via HTTPS using --url https://host:8443, reads the client certificate and key from ~/.config/incus/ unless --cert and --key are passed through options. Server trust is established with --server-cert, or skipped verification with --insecure. For development purposes local connections using a Unix socket is supported. Sockets are found via --socket, $INCUS_SOCKET, $INCUS_DIR/unix.socket, /var/lib/incus/unix.socket, then /run/incus/unix.socket.

## Commands

The instance manager supports the following commands:

* list / show: GET /1.0/instances?recursion=2 for the table, and recursion=1 for show. The list supports table, csv, json and yaml. YAML output needs PyYAML if you have it, otherwise it falls back to JSON.
* create: POST /1.0/instances followed by a state change if you pass --start. The images:, ubuntu: and ubuntu-daily: remotes are resolved to their simplestreams servers, and local aliases or fingerprints also work.
* update: a GET and a PUT guarded by If-Match, so it fails instead of overwriting a concurrent change. --unset-config really removes keys this way.
* start / stop / restart / delete: PUT .../state and DELETE. With --force, delete stops the instance first.
* snapshot / backup: these use the snapshot endpoints, and backup creates a server-side backup, downloads it, then deletes the staged copy.
* Asynchronous calls: the script waits for each operation to finish and reports its error if it fails.

## Global Options

| Option | Purpose |
| --- | --- |
| --socket PATH | Unix socket path |
| --url URL	HTTPS | endpoint, e.g. https://host:8443 |
| --cert FILE | Client certificate (default ~/.config/incus/client.crt) |
| --key FILE | Client key (default ~/.config/incus/client.key) |
| --server-cert FILE | Server certificate or CA to trust |
| --insecure | Skip server certificate verification |

The environment variables `INCUS_SOCKET`, `INCUS_DIR` (for socket lookup) and `INCUS_CONF` (client cert directory) are also read.

## Command Options

Every command also accepts `--project NAME`, which the table leaves out.

Command |	Positional Arguments |	Options |
| --- | --- | --- |
| list |	none |	--format {table,json,yaml,csv} (default table) |
| show |	instance |	none |
| create |	instance, source |	--vm, --start, --profile NAME (repeatable), --config KEY=VALUE (repeatable), --device NAME,TYPE,KEY=VALUE,... (repeatable) |
| update |	instance |	--config KEY=VALUE (repeatable), --unset-config KEY (repeatable), --device NAME,KEY=VALUE,... (repeatable), --description TEXT |
| delete |	instance |	--force |
| start |	instance |	none |
| stop |	instance |	--force, --timeout SECONDS (default 30) |
| restart |	instance |	--force |
| console |	instance |	--show-log (required in practice, since interactive mode isn’t supported) |
| exec |	instance, command... |	none (the command goes after --) |
| snapshot | list	instance |	none |
| snapshot | create	instance, snapshot |	--stateful |
| snapshot | restore	instance, snapshot |	--stateful |
| snapshot | delete	instance, snapshot |	none |
| backup |	instance |	--output FILE (required), --instance-only, --optimized-storage |

### Notes

* update requires at least one of --config, --unset-config, --device or --description.
* create accepts a source of images:…, ubuntu:…, ubuntu-daily:…, local:…, a bare local alias, or a 64-character image fingerprint.
* restart has no --timeout, so it uses the server default.
