# Phase 6: Network & Firewall Architecture

**Document:** Network Topology and Port Security  
**Scope:** Campus LAN and Ingress Boundaries  

---

## 1. Firewall & Port Allocation Matrix

| Service | Internal Port | External Port | Protocol | Scope | Exposure |
|---|---|---|---|---|---|
| Nginx Edge Proxy | 80 / 443 | 80 / 443 | TCP | Public / Campus WAN | **EXPOSED** |
| Gunicorn (Django) | 8000 | None | TCP | Docker Network (`labora-internal`) | **BLOCKED** |
| PostgreSQL 16 | 5432 | None | TCP | Docker Network (`labora-internal`) | **BLOCKED** |
| Redis 7 Broker | 6379 | None | TCP | Docker Network (`labora-internal`) | **BLOCKED** |
| Judge0 API | 2358 | None | TCP | Docker Network (`labora-internal`) | **BLOCKED** |
| Judge0 DB | 5432 | None | TCP | Docker Network (`judge0-net`) | **BLOCKED** |
| Judge0 Redis | 6379 | None | TCP | Docker Network (`judge0-net`) | **BLOCKED** |

> **CRITICAL SECURITY RULE:** Only ports 80 and 443 (Nginx) may be permitted inbound through the firewall. All database, queue, cache, and sandbox interfaces must strictly remain on internal Docker bridge networks.

---

## 2. Ingress & CGNAT Strategies

1. **Option A: Static Public IP (Standard)**
   - College network administrator assigns public IP and maps ports 80/443 to the LABORA server.
   - Domain A-record points to public IP (e.g. `labora.college.edu`).
   - Free Let's Encrypt SSL certificate provisioned automatically via Certbot.

2. **Option B: CGNAT / Inbound Blocked (Zero-Cost Tunnel)**
   - If the college ISP blocks inbound connections or uses CGNAT, deploy **Cloudflare Zero Trust Tunnel** (`cloudflared` free tier).
   - Establishes outbound-only HTTPS tunnel from server to Cloudflare edge; no public IP or firewall port forwards needed.

3. **Option C: Closed Campus Intranet (On-Premise Only)**
   - Server resides solely on the campus LAN / lab subnet (e.g. `192.168.10.50`).
   - Lab client computers connect via internal DNS or IP.
   - Uses an institutional CA-signed certificate installed on client lab PCs.
