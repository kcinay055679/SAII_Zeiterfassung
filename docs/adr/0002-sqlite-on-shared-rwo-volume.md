# SQLite on one RWO volume shared by three prod replicas

The deck requires both three prod replicas and PVC persistence under `/data`. In general those conflict (RWO, one volume). We keep both: all replicas run on one node (ADR-0001), share one SQLite file on the volume, and rely on SQLite's file locking to serialize writes. The status check and the insert of a stamp run in one write transaction, so two replicas can't both accept EIN for the same Person.

## Considered Options

- **JSONL + `flock`** (the original plan, matches the course's `times.jsonl`): rejected because the Valid transition check needs read-then-write atomicity and per-Person queries, which SQLite gives us directly.
- **One replica in prod**: violates the deck.
- **Separate database pod (Postgres)**: correct for real multi-node scale, but out of scope.

## Consequences

Works only while every replica shares one kernel and one local filesystem. On a networked or multi-node volume, SQLite locking is not reliable.
