# Phase 6: Production Deployment Guide

**Target Environment:** Ubuntu Server 22.04 / 24.04 LTS  
**Software Target:** Docker Engine 24+ & Docker Compose v2  
**Budget Objective:** ₹0 Software Expenditure (Self-Hosted)  

---

## 1. Host Preparation & Docker Installation

```bash
# Update Ubuntu package indexes
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker Engine and Docker Compose
sudo apt-get install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Enable cgroups v1 / v2 for Judge0 sandbox compliance
sudo systemctl enable docker
sudo systemctl start docker
```

---

## 2. Deploying LABORA Production Stack

```bash
# 1. Clone repository into /opt/labora
sudo mkdir -p /opt/labora && sudo chown -R $USER:$USER /opt/labora
cd /opt/labora

# 2. Configure production secrets
cd production_kit/docker
cat << 'EOF' > .env
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_DB=labora
POSTGRES_USER=labora_admin
POSTGRES_PASSWORD=$(openssl rand -hex 24)
REDIS_PASSWORD=$(openssl rand -hex 24)
LABORA_SECURE_BROWSER_KEY=$(openssl rand -hex 32)
DOMAIN_NAME=labora.yourcollege.edu
EOF

# 3. Launch all containers
docker compose -f docker-compose.prod.yml up -d

# 4. Apply database migrations
docker exec -it labora-backend python manage.py migrate

# 5. Create superuser
docker exec -it labora-backend python manage.py createsuperuser

# 6. Verify health
bash ../scripts/health_check.sh
```
