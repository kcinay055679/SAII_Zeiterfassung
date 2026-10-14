# Zeiterfassung

A small time-tracking service where people clock in, take breaks and clock out through a web page. Built for the SAII HS2026 Kubernetes assignment and deployed as a dev and a prod environment.

## Language

### Tracking

**Person**:
Someone who stamps, identified only by the name they type in. Names match case-insensitively with surrounding whitespace ignored; the spelling of the first stamp is the one shown.
_Avoid_: User, employee, account

**Stamp**:
One recorded event: a Person, an Action, an optional Note and the time it happened. Stamps are append-only.
_Avoid_: Entry, record, booking, Stempelung (in English text)

**Action**:
One of the four stamp kinds: EIN (clock in), PAUSE (start break), ZURUECK (end break), AUS (clock out). The UI label for ZURUECK is "ZURÜCK".
_Avoid_: Event type, command

**Note**:
Optional free text attached to a Stamp, up to 200 characters, e.g. "Support XYZ Kunde Meyer".
_Avoid_: Comment, description (the course calls it "Rapport")

**Status**:
Where a Person currently stands, derived from their latest Stamp: OUT (no stamp, or last was AUS), WORKING (last was EIN or ZURUECK), ON BREAK (last was PAUSE).
_Avoid_: State, presence

**Valid transition**:
An Action allowed from the Person's current Status. OUT allows EIN; WORKING allows PAUSE or AUS; ON BREAK allows ZURUECK. Anything else is rejected.

**Worked time today**:
The sum of WORKING intervals for a Person within the current day in Europe/Zurich. An interval still open counts up to now.
_Avoid_: Hours, balance

**Status board**:
The overview on the main page listing every Person with their Status and Worked time today.

### Deployment

**Environment**:
Either dev or prod. Same base manifests, different overlays.

**Dev**:
One replica, reachable through a NodePort, running an image imported straight into the cluster.

**Prod**:
Three replicas behind a ClusterIP service and an Ingress, pulling the image from the cluster's local registry.
