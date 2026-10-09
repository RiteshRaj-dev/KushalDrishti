# Privacy note (designed to follow the DPDP Act 2023; get legal review before roll-out)
**Used:** anonymous body counts per room, equipment status, camera health, and a blurred 480p evidence photo on a confirmed breach.
**Never used or stored:** face recognition, face templates, names, gender, age, raw video, unblurred faces.
**How:** faces are blurred in memory before counting, saving or sending. Raw frames are never written to disk by the pipeline.
**Honest limits**
- The face finder is a basic frontal detector. A face turned away can be missed, so the blur is best effort. A stronger detector is a drop-in change in `kd_edge/privacy.py`.
- `kd_edge.evaluate prepare` saves RAW frames so you can label them. Keep that folder private and delete it after labelling. It is git-ignored.
- Counting is not consent. Put a notice board at each centre that explains the camera counting.
**Proposals for the policy owner (not decided by this code):** keep evidence photos for a fixed period (for example 90 days), log who opened each notice, and give trainees a way to ask questions.
