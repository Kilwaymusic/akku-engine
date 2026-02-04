import { spawn } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

const GCP_HOST = '34.134.82.224';
const GCP_USER = 'composerkil';
const GCP_PROJECT_PATH = '/home/composerkil/akku-engine';

interface DeployResult {
  success: boolean;
  message: string;
  output?: string;
}

// Setup SSH key from environment
async function setupSSHKey(): Promise<string> {
  let sshKeyData = process.env.GCP_SSH_PRIVATE_KEY;
  if (!sshKeyData) {
    throw new Error('GCP_SSH_PRIVATE_KEY not found in environment');
  }

  let sshKey: string;
  
  // Check if it's Base64 encoded (starts with typical OpenSSH base64 chars)
  if (sshKeyData.startsWith('b3BlbnNzaC') || !sshKeyData.includes('-----BEGIN')) {
    // Remove all whitespace from base64 before decoding
    const cleanBase64 = sshKeyData.replace(/\s+/g, '');
    // Decode base64
    sshKey = Buffer.from(cleanBase64, 'base64').toString('utf-8');
  } else {
    // Already plain text
    sshKey = sshKeyData;
  }
  
  // Ensure proper line endings and format
  if (!sshKey.endsWith('\n')) {
    sshKey += '\n';
  }
  
  // Write to temp file
  const sshDir = path.join(os.tmpdir(), '.ssh');
  if (!fs.existsSync(sshDir)) {
    fs.mkdirSync(sshDir, { mode: 0o700 });
  }
  
  const keyPath = path.join(sshDir, 'gcp_key');
  fs.writeFileSync(keyPath, sshKey, { mode: 0o600 });
  
  return keyPath;
}

// Execute SSH command on GCP
async function sshExec(keyPath: string, command: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const args = [
      '-i', keyPath,
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'UserKnownHostsFile=/dev/null',
      '-o', 'ConnectTimeout=10',
      `${GCP_USER}@${GCP_HOST}`,
      command
    ];

    const proc = spawn('ssh', args);
    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => { stdout += data.toString(); });
    proc.stderr.on('data', (data) => { stderr += data.toString(); });

    proc.on('close', (code) => {
      if (code === 0) {
        resolve(stdout);
      } else {
        reject(new Error(`SSH command failed (code ${code}): ${stderr}`));
      }
    });

    proc.on('error', reject);
  });
}

// Upload file to GCP via SCP
async function scpUpload(keyPath: string, localPath: string, remotePath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const args = [
      '-i', keyPath,
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'UserKnownHostsFile=/dev/null',
      localPath,
      `${GCP_USER}@${GCP_HOST}:${remotePath}`
    ];

    const proc = spawn('scp', args);
    let stderr = '';

    proc.stderr.on('data', (data) => { stderr += data.toString(); });

    proc.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(new Error(`SCP upload failed: ${stderr}`));
      }
    });

    proc.on('error', reject);
  });
}

// Deploy a Python script to GCP
export async function deployScript(scriptName: string, content: string): Promise<DeployResult> {
  try {
    const keyPath = await setupSSHKey();
    
    // Write content to temp file
    const tempFile = path.join(os.tmpdir(), scriptName);
    fs.writeFileSync(tempFile, content);
    
    // Upload to GCP
    const remotePath = `${GCP_PROJECT_PATH}/${scriptName}`;
    await scpUpload(keyPath, tempFile, remotePath);
    
    // Clean up temp file
    fs.unlinkSync(tempFile);
    
    return {
      success: true,
      message: `Successfully deployed ${scriptName} to GCP`
    };
  } catch (error) {
    return {
      success: false,
      message: `Failed to deploy: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

// Restart Flask server on GCP
export async function restartServer(): Promise<DeployResult> {
  try {
    const keyPath = await setupSSHKey();
    
    // Kill existing Flask process and restart
    const command = `cd ${GCP_PROJECT_PATH} && pkill -f "python3 app.py" 2>/dev/null; nohup python3 app.py > server.log 2>&1 &`;
    await sshExec(keyPath, command);
    
    // Wait a moment for server to start
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Check if server is running
    const checkCommand = `curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/health 2>/dev/null || echo "000"`;
    const statusCode = await sshExec(keyPath, checkCommand);
    
    if (statusCode.trim() === '200') {
      return {
        success: true,
        message: 'Flask server restarted successfully'
      };
    } else {
      return {
        success: true,
        message: 'Flask server restart command sent (status check returned: ' + statusCode.trim() + ')'
      };
    }
  } catch (error) {
    return {
      success: false,
      message: `Failed to restart server: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

// Deploy and restart in one operation
export async function deployAndRestart(scripts: { name: string; content: string }[]): Promise<DeployResult> {
  try {
    // Deploy all scripts
    for (const script of scripts) {
      const result = await deployScript(script.name, script.content);
      if (!result.success) {
        return result;
      }
      console.log(`[GCP Deploy] ${result.message}`);
    }
    
    // Restart server
    const restartResult = await restartServer();
    console.log(`[GCP Deploy] ${restartResult.message}`);
    
    return {
      success: true,
      message: `Deployed ${scripts.length} script(s) and restarted server`
    };
  } catch (error) {
    return {
      success: false,
      message: `Deployment failed: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}

// Test GCP connection
export async function testConnection(): Promise<DeployResult> {
  try {
    const keyPath = await setupSSHKey();
    const output = await sshExec(keyPath, 'echo "Connection successful" && ls -la ' + GCP_PROJECT_PATH);
    
    return {
      success: true,
      message: 'GCP connection successful',
      output
    };
  } catch (error) {
    return {
      success: false,
      message: `Connection failed: ${error instanceof Error ? error.message : String(error)}`
    };
  }
}
