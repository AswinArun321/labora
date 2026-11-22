# Phase 0: Stakeholder Decision Register & Open Questions

**Reference:** `plann.md` Section 2.3 & Section 22, `LABORA_updated_completion_plan.md` Section 6  
**Status:** Ready for College IT & Academic Stakeholder Review  

The following items must be confirmed by the college administration and technical team before production hardware allocation and exam rollout:

---

## 1. Workload & Sizing Requirements
* [ ] **Q1: Peak Simultaneous Executions:** While 1,000 students are concurrently logged in, editing, and reading, how many students are expected to click "Run" at the exact same second? (Engineering recommended baseline: 100 simultaneous execution slots).
* [ ] **Q2: Traffic Arrival Profile:** Is code execution expected to arrive as a steady trickle throughout the 2-hour lab, or in synchronized spikes (e.g. right after a question is announced, or 5 minutes before the exam ends)?
* [ ] **Q3: Exam Session Schedule:** How many distinct lab exam batches will be held per day, and what is the typical duration of each exam session (e.g. 2 hours or 3 hours)?

---

## 2. Hardware & Infrastructure Availability
* [ ] **Q4: Available Physical/Virtual Servers:** What existing college-owned servers or virtualization hosts (VMware, Proxmox, Hyper-V, or bare-metal Ubuntu) are allocated for LABORA?
* [ ] **Q5: Server Hardware Specifications:** For each candidate machine, what are the CPU models, physical core counts, available RAM, and storage types (NVMe, SATA SSD, or HDD)?
* [ ] **Q6: Storage Redundancy & UPS:** Are the servers equipped with RAID arrays and connected to a battery UPS capable of at least 30 minutes of backup runtime?

---

## 3. Network & Ingress Access
* [ ] **Q7: Public IP & Port Availability:** Does the college ISP connection provide a static public IP address with inbound TCP 443 permitted through the campus firewall, or is the network behind Carrier-Grade NAT (CGNAT)?
* [ ] **Q8: Ingress Strategy:** If behind CGNAT, does college IT approve an internal-only deployment (LAN/Wi-Fi only) or a secure reverse tunnel (e.g. Cloudflare Zero Trust Tunnel)?
* [ ] **Q9: Bandwidth Capacity:** What is the dedicated upload and download bandwidth allocated to the lab server?

---

## 4. Academic Identity & Policy
* [ ] **Q10: Student Login Identifiers:** Will student accounts be identified by University Registration Number / Roll Number (e.g. `21MCA042`) or college email addresses?
* [ ] **Q11: Data Retention Compliance:** What is the institutional retention requirement for student submissions, execution audit logs, and generated lab records (e.g., 3 years or 5 years for accreditation audits like NBA/NAAC)?
* [ ] **Q12: Client Lab Machine Fleet:** What operating system versions are installed on the college lab computers (Windows 10, Windows 11, or Linux)?
