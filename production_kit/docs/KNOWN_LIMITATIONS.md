# LABORA — Known Limitations & Operational Constraints

**Document:** `production_kit/docs/KNOWN_LIMITATIONS.md`  
**Date:** 22 November 2026  

---

## 1. Client-Side Kiosk Limitations

1. **Physical Hardware Oversight:** The Electron Secure Browser locks down the software window and monitors OS processes. It cannot prevent students from viewing physical mobile devices, handwritten notes, or using hardware video capture devices (e.g. HDMI splitters). Physical proctoring by lab teachers remains necessary.
2. **Windows Code-Signing:** Unless signed with an institutional Microsoft Authenticode certificate, Windows Defender SmartScreen may display an "Unrecognized app" prompt on initial launch. Administrators should whitelist the executable via Active Directory GPO.

---

## 2. Infrastructure & Execution Limitations

1. **Single-Host vs. Multi-Host Sizing:** If running all services (Web, DB, Redis, Celery, and Judge0) on a single physical machine, heavy compilation of C and Java programs may cause temporary CPU spikes. A 2-host topology separating web/database from Judge0 execution is recommended for 1,000 active students.
2. **Concurrent Sandbox Capacity:** While 1,000 students can concurrently read questions, write code, and autosave, physical CPU cores limit concurrent compilations. A queue depth of 100 concurrent execution slots ensures queue delays remain under 5 seconds.
3. **Storage Growth:** Autosaved code versions and activity events grow over time. Administrators should schedule the provided database pruning scripts at the end of each academic semester.
