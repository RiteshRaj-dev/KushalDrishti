# Before real use
1. **Broker:** TLS 1.3, one login per centre, ACL so a centre can publish only to its own `msde/telemetry/<code>` and `msde/evidence/<code>/#` (template in `mosquitto/mosquitto.conf`).
2. **Keys:** replace the single master secret with a per-device key store. Set `KD_MASTER_SECRET` and `KD_API_KEY` from a secret manager, never from the repo.
3. **Officers:** sign-in through the department's SSO, keep an audit log of who opened and approved each notice. `KD_API_KEY` is only a stop-gap.
4. **Licences:** see NOTICE.md (YOLOv8 is AGPL-3.0).
5. **Data:** set a retention rule for evidence photos, back up PostgreSQL, vendor Leaflet files for air-gapped sites.
6. **Scale:** the demo runs 12 centres. At 15,000 centres with one packet a minute the broker sees about 250 messages a second, which is small, but run a load test and add database indexes and partitioning before claiming it.
7. **Accuracy:** measure on real footage from several centres (lighting, camera angle, crowding) and publish the table.
