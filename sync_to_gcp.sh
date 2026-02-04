#!/bin/bash
# Akku SDK GCP Sync Script
# Syncs local SDK code to GCP Worker via SSH
set -e

GCP_HOST="${GCP_HOST:-34.134.82.224}"
GCP_USER="${GCP_USER:-composerkil}"
GCP_BASE="/home/${GCP_USER}/akku-engine"

echo "=== Akku SDK GCP Sync ==="
echo "Target: ${GCP_USER}@${GCP_HOST}"
echo "Syncing local SDK to GCP Worker..."

if [ ! -d "server/akku_sdk" ]; then
    echo "ERROR: server/akku_sdk directory not found. Run from project root."
    exit 1
fi

tar -czf /tmp/akku_sdk.tar.gz -C server akku_sdk gcp-app.py || {
    echo "ERROR: Failed to create tar archive"
    exit 1
}

echo "Uploading SDK to GCP..."
scp /tmp/akku_sdk.tar.gz ${GCP_USER}@${GCP_HOST}:/tmp/ || {
    echo "ERROR: SCP failed. Check SSH key and connectivity."
    rm -f /tmp/akku_sdk.tar.gz
    exit 1
}

echo "Extracting and restarting on GCP..."
ssh ${GCP_USER}@${GCP_HOST} << ENDSSH
set -e
cd ${GCP_BASE}
mv server/akku_sdk server/akku_sdk.bak.\$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
tar -xzf /tmp/akku_sdk.tar.gz -C server/
pkill -f "python.*gcp-app.py" || true
sleep 1
cd ${GCP_BASE}/server
nohup python gcp-app.py > /tmp/gcp-worker.log 2>&1 &
sleep 2
if pgrep -f "python.*gcp-app.py" > /dev/null; then
    echo "GCP Worker restarted successfully"
else
    echo "WARNING: GCP Worker may not have started"
fi
rm -f /tmp/akku_sdk.tar.gz
ENDSSH

echo "=== Sync Complete ==="
rm -f /tmp/akku_sdk.tar.gz
