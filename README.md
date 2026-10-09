# dnstriage

A small inference service that classifies DNS domains as GOOD, WARN, BAD or UNKNOWN, using curated lists first and falling back to an LLM for unknown domains.

> **Status: work in progress.**
> Quick start, configuration and a sample run will appear here as features land.

## Documents

- [DESIGN.md](DESIGN.md): purpose, architecture, decisions and threat model.
- [CLAUDE.md](CLAUDE.md) and [.claude/](.claude): how this project is built with Claude Code.

## Scope

This is a proof of concept. DNS logs are pushed to this service, while reports are pulled.

## Outside of Scope
* Event Collection - DNS logs need to be transformed and pushed to this service. Log collection, encrypted DNS (DoH/DoT) or VPNs are all outside of this service and would need to be dealt with upstream.
* Retention - Currently uses an in-memory data store, so state is lost on restart. This would need to move to a permanent DB such as SQLite or Postgres.
* Alerting - Service doesn't have a threshold for how many bad-domains or any severity level for a query.
* Context - There are good reasons for accessing BAD domains - this service only tracks, it makes no judgement as to if a node is compromised or not.
* Security - No authentication, authorisation or TLS. Any client that can reach the service can push logs and read reports. Run it on a trusted network, or put it behind a reverse proxy that handles TLS and authentication.
