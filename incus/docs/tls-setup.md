# Restricted Incus 7.0 LTS client setup — local pool example

The values here describe `pool.example.yaml`; generic provider configuration
requires an explicit endpoint, remote, non-default project, and subnet.

These are **manual administrator/controller steps**, not automated provider
bootstrap. Do not run them through Codex against ignored credentials. Lifecycle
control subsequently uses TLS only, with no host SSH or incus-admin membership
for the controller.

## Server administrator, at the VM console

Confirm existing project, bridge and storage; do not recreate or remove them:

```sh
incus project show eve-ci
incus network show incusbr0
incus storage show default
incus list --project eve-ci
```

Review existing consumers before changing quotas/settings. Apply intended limits
and disable IPv6 on the existing bridge:

```sh
incus project set eve-ci limits.instances=3 limits.cpu=6 limits.memory=6GiB
incus network set incusbr0 ipv4.address=10.201.153.1/24 ipv4.nat=false ipv6.address=none
incus config set core.https_address 192.168.1.108:8443
```

`eve-ci` must have `features.images=true` (preloaded project images), access to
pool `default`, and access to managed network `incusbr0`. If that bridge is in
the default project, configure `features.networks=false` for `eve-ci` before
using it, according to existing project/network consumers. Restrict project
security-sensitive device/container options as appropriate; the provider only
requests unprivileged containers, one managed NIC, and one root disk. The
controller's certificate must not be authorized for the default project.

Limit LAN firewall TCP 8443 to the **explicit controller address**. Do not expose
8443 on WAN, use a trust password, or join the controller to `incus-admin`.

## Controller: create one dedicated TLS client identity

Choose an explicit absolute directory; do not use an ambient Incus directory.
Set `INCUS_CONF` for these commands only. Incus 7.0 uses `client.crt`,
`client.key`, `config.yml`, and `servercerts/<remote>.crt` there.

```sh
install -d -m 700 /absolute/controller/eve-incus-client
install -d -m 700 /absolute/controller/eve-incus-client/servercerts
umask 077
openssl req -x509 -newkey rsa:4096 -nodes -sha256 -days 365 \
  -subj /CN=eve-ci-controller \
  -keyout /absolute/controller/eve-incus-client/client.key \
  -out /absolute/controller/eve-incus-client/client.crt
chmod 600 /absolute/controller/eve-incus-client/client.key
```

Transfer **only client.crt** to the server administrator over your authenticated
out-of-band channel. Never transfer the client private key. At the VM console:

```sh
incus config trust add-certificate /explicit/transferred/client.crt \
  --name eve-ci-controller --restricted --projects eve-ci
incus config trust list --format=json
incus config trust show <full-client-certificate-fingerprint>
```

Verify `restricted: true`, `projects: [eve-ci]`, and type `client`.

## Pin and verify the server certificate

The administrator obtains the Incus server certificate at the VM console
(normally `/var/lib/incus/server.crt`) and computes:

```sh
openssl x509 -in /var/lib/incus/server.crt -noout -fingerprint -sha256
```

Transfer **that public server certificate** to the controller through the same
authenticated channel, verify its SHA-256 fingerprint against the console
value, then install it as
`/absolute/controller/eve-incus-client/servercerts/eve-incus-pool.crt`.
Do not fetch a certificate from an untrusted network and automatically accept it.

Create this explicit non-secret `config.yml` in the private client directory:

```yaml
default-remote: eve-incus-pool
remotes:
  eve-incus-pool:
    addr: https://192.168.1.108:8443
    auth_type: tls
    project: eve-ci
    protocol: incus
    public: false
  images:
    addr: https://images.linuxcontainers.org
    protocol: simplestreams
    public: true
```

No insecure remote-add flag, trust-password, skip-verification, or unrestricted
join token is used. Pinned certificate validation is handled by the official
client; the public image server uses normal CA verification. Certificate rotation
requires explicit out-of-band verification and pin replacement.

Verify authorized access and **denial** of the default project manually:

```sh
INCUS_CONF=/absolute/controller/eve-incus-client incus list eve-incus-pool: --project eve-ci
INCUS_CONF=/absolute/controller/eve-incus-client incus list eve-incus-pool: --project default
```

The second command must fail. If it succeeds, stop: remove/correct the server
trust entry before using this provider. Selecting a project on a remote alone
does not restrict authorization. No default-project probe is performed by the
provider itself: every one of its API/client operations is scoped to `eve-ci`.

Configure an explicit controller SSH Ed25519 public/private pair independently;
Eve neither inspects nor generates an ambient SSH private key. Preload the cloud
image with the administrator's identity as documented in the provider README.
Verify routed access and the controller firewall before opting into the live test.

Authoritative Incus 7.0 references:

* [Project TLS confinement](https://github.com/lxc/incus/blob/v7.0.0/doc/howto/projects_confine.md)
* [HTTPS exposure](https://github.com/lxc/incus/blob/v7.0.0/doc/howto/server_expose.md)
* [Project resource limits](https://github.com/lxc/incus/blob/v7.0.0/doc/reference/projects.md)
* [Official create/init implementation](https://github.com/lxc/incus/blob/v7.0.0/cmd/incus/create.go)
