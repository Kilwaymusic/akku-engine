#!/bin/bash
set -e

GCP_HOST="34.134.82.224"
GCP_USER="composerkil"
REMOTE_DIR="/home/composerkil/akku-engine"
LOCAL_SDK_DIR="server/akku_sdk"

echo "=============================================="
echo "Akku SDK Deployment to GCP Worker"
echo "=============================================="

if [ -z "$GCP_SSH_PRIVATE_KEY" ]; then
    echo "Error: GCP_SSH_PRIVATE_KEY environment variable not set"
    exit 1
fi

echo "[1/4] Setting up SSH key..."
mkdir -p ~/.ssh
echo "$GCP_SSH_PRIVATE_KEY" > ~/.ssh/gcp_key
chmod 600 ~/.ssh/gcp_key

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/gcp_key"

echo "[2/4] Testing SSH connection..."
ssh $SSH_OPTS $GCP_USER@$GCP_HOST "echo 'Connection successful'"

echo "[3/4] Deploying SDK files..."
scp $SSH_OPTS -r $LOCAL_SDK_DIR/*.py $GCP_USER@$GCP_HOST:$REMOTE_DIR/akku_sdk/

echo "[4/4] Deploying GCP app..."
scp $SSH_OPTS server/gcp-app.py $GCP_USER@$GCP_HOST:$REMOTE_DIR/gcp-app.py

echo ""
echo "Restarting Flask server..."
ssh $SSH_OPTS $GCP_USER@$GCP_HOST "cd $REMOTE_DIR && pkill -f 'python.*gcp-app.py' || true; nohup python3 gcp-app.py > /tmp/akku-worker.log 2>&1 &"

echo ""
echo "=============================================="
echo "Deployment complete!"
echo "=============================================="
echo ""
echo "Check worker status: curl http://$GCP_HOST:5000/health"

rm -f ~/.ssh/gcp_key
