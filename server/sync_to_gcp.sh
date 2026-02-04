#!/bin/bash
# Sync SDK files to GCP Worker Server
# Run this script on a machine with SSH access to GCP

GCP_HOST="composerkil@34.134.82.224"
SDK_DIR="~/akku-engine/akku_sdk"

echo "=== Akku SDK v3.6 GCP Sync ==="
echo "Syncing SDK files to $GCP_HOST..."

# Create tarball of SDK files
tar -czf /tmp/akku_sdk.tar.gz -C server akku_sdk

# Upload to GCP
scp /tmp/akku_sdk.tar.gz $GCP_HOST:/tmp/

# Extract on GCP and restart Flask server
ssh $GCP_HOST << 'EOF'
cd ~/akku-engine
# Backup current SDK
mv akku_sdk akku_sdk_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null
# Extract new SDK
tar -xzf /tmp/akku_sdk.tar.gz
echo "SDK files updated!"
# Restart Flask (if using systemd)
# sudo systemctl restart akku-worker
# Or if using screen/tmux
# killall python && cd ~/akku-engine && python gcp-app.py &
echo "Please manually restart the Flask server if needed"
EOF

# Also upload the updated gcp-app.py
scp server/gcp-app.py $GCP_HOST:~/akku-engine/gcp-app.py

echo "=== Sync Complete ==="
echo "Remember to restart the Flask server on GCP!"
