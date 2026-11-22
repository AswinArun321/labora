# Phase 10: College Hardware Allocation & Capacity Sizing

**Document:** Hardware Requirements & Host Topology  
**Target:** 1,000 Concurrent Students at ₹0 Additional Hardware Purchase  

---

## 1. Minimum vs. Recommended Hardware Specifications

| Resource | Single-Server Minimum (Pilot) | Recommended 2-Server Topology (Production) |
|---|---|---|
| **Architecture** | 1 Host (App + DB + Judge0) | Host 1: Web & DB \| Host 2: Judge0 Sandbox |
| **CPU** | 8 Cores / 16 Threads (Intel Xeon / AMD Ryzen) | Host 1: 8 Cores \| Host 2: 8–16 Cores |
| **RAM** | 32 GB RAM | Host 1: 16 GB RAM \| Host 2: 16–32 GB RAM |
| **Storage** | 500 GB NVMe / SATA SSD | Host 1: 250 GB SSD \| Host 2: 250 GB SSD |
| **Network** | 1 Gbps Ethernet | 1 Gbps Ethernet (isolated inter-server VLAN) |
| **UPS Backup** | 1 kVA Battery (30 min runtime) | 2 kVA Battery (30–60 min runtime) |

---

## 2. Multi-Host Placement Strategy

```
┌────────────────────────────────────────────────────────┐
│ HOST 1: Application & Database Server (16GB RAM)       │
│ - Nginx Edge Reverse Proxy (Ports 80/443)              │
│ - Gunicorn Django Web Workers (4 Workers)              │
│ - PostgreSQL 16 Database Server                        │
│ - Redis 7 Message Queue Broker                         │
│ - Celery Dispatcher & Document Generation Workers      │
└────────────────────────────────────────────────────────┘
                           │ (Private 1Gbps LAN)
┌────────────────────────────────────────────────────────┐
│ HOST 2: Dedicated Execution Sandbox Host (16-32GB RAM) │
│ - Judge0 CE Execution Daemon (Port 2358 internal)      │
│ - Judge0 Isolated Postgres DB & Redis                  │
│ - Linux cgroups v1/v2 process sandboxing               │
│ - GCC, JDK, and Python execution environments          │
└────────────────────────────────────────────────────────┘
```
