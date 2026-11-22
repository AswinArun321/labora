# Phase 10: Campus Network Readiness & Ingress Audit

**Document:** Network Readiness Assessment  
**Audience:** College Network Administrator  

---

## 1. Bandwidth Sizing Model for 1,000 Concurrent Students

* **Static SPA Asset Loading:** React bundle + Monaco Editor (~3.5 MB per client).
  - 1,000 students opening the browser simultaneously: $3.5\text{ GB}$ total download.
  - On a 1 Gbps campus LAN: downloads complete in **< 35 seconds**.
  - Subsequent requests are served from local browser disk cache (`Cache-Control: public, immutable`).
* **Autosave & Telemetry Bandwidth:**
  - 1,000 students autosaving code (~2 KB) every 15 seconds:
    $$\frac{1,000 \times 2\text{ KB}}{15\text{ s}} \approx 133\text{ KB/sec} \approx 1.1\text{ Mbps}$$
  - Extremely light traffic well within standard 100 Mbps / 1 Gbps campus network limits.

---

## 2. Network Infrastructure Checklist

- [ ] **Wired Lab Ethernet:** Client computers in computer labs connected via 100/1000 Mbps managed switches.
- [ ] **VLAN Segregation:** Recommend placing lab exam computers on a dedicated Exam VLAN with outbound internet blocked during exam hours.
- [ ] **DNS Resolution:** Local campus DNS server configured to resolve `labora.college.edu` to internal server IP (e.g. `192.168.10.50`).
- [ ] **NTP Clock Synchronization:** Server and client lab PCs must synchronize time via campus NTP server to maintain clock skew within 300 seconds for HMAC validation.
