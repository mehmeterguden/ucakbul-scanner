# ucakbul-scanner

Public, data-only flight price scanner (no personal data). Every 3 hours it queries Google Flights (via [fli](https://github.com/punitarani/fli))
for Madrid ↔ ~90 European city groups for a few target weekends (`targets.json`), split into parallel shards, and publishes the latest result
as release assets (`data` release → `latest-<window>.json`). A private repo consumes it, scores routes and sends alerts.
