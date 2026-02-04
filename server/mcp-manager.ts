import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { BlenderMCPClient, executeGenerationPlan, CharacterGenerationPlan } from './blender-mcp-client';

// ESM compatibility for __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class MCPManager {
  private blenderProcess: ChildProcess | null = null;
  private client: BlenderMCPClient | null = null;
  private port: number = 9876;
  private isReady: boolean = false;
  private startupPromise: Promise<void> | null = null;

  async ensureBlenderRunning(): Promise<void> {
    if (this.isReady && this.client?.isConnected()) {
      return;
    }

    if (this.startupPromise) {
      return this.startupPromise;
    }

    this.startupPromise = this._startBlender();
    await this.startupPromise;
    this.startupPromise = null;
  }

  private async _startBlender(): Promise<void> {
    // Kill any existing process
    this.stopBlender();

    return new Promise((resolve, reject) => {
      const addonPath = path.resolve(__dirname, '../scripts/blender_mcp_addon.py');
      
      console.log(`Starting Blender MCP server on port ${this.port}...`);
      console.log(`Addon path: ${addonPath}`);

      // Check if blender is available
      this.blenderProcess = spawn('blender', [
        '--background',
        '--python', addonPath,
        '--', String(this.port)
      ], {
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let started = false;
      const timeout = setTimeout(() => {
        if (!started) {
          reject(new Error('Blender startup timeout'));
        }
      }, 30000);

      this.blenderProcess.stdout?.on('data', (data: Buffer) => {
        const output = data.toString();
        console.log('[Blender]', output);
        
        if (output.includes('MCP server started') || output.includes('Waiting for commands')) {
          if (!started) {
            started = true;
            clearTimeout(timeout);
            
            // Wait a bit for the server to be fully ready, then connect
            setTimeout(async () => {
              try {
                await this._connectClient();
                resolve();
              } catch (error) {
                reject(error);
              }
            }, 1000);
          }
        }
      });

      this.blenderProcess.stderr?.on('data', (data: Buffer) => {
        console.error('[Blender Error]', data.toString());
      });

      this.blenderProcess.on('error', (error) => {
        console.error('Failed to start Blender:', error);
        clearTimeout(timeout);
        this.isReady = false;
        reject(error);
      });

      this.blenderProcess.on('exit', (code) => {
        console.log(`Blender process exited with code ${code}`);
        this.isReady = false;
        if (!started) {
          clearTimeout(timeout);
          reject(new Error(`Blender exited with code ${code}`));
        }
      });
    });
  }

  private async _connectClient(): Promise<void> {
    this.client = new BlenderMCPClient('localhost', this.port);
    await this.client.connect();
    this.isReady = true;
    
    // Test connection
    const info = await this.client.getSceneInfo();
    console.log('Connected to Blender MCP. Scene info:', info);
  }

  async generateCharacter(
    plan: CharacterGenerationPlan,
    outputPath: string
  ): Promise<{ success: boolean; modelPath?: string; error?: string; log: string[] }> {
    try {
      await this.ensureBlenderRunning();
      
      if (!this.client) {
        throw new Error('MCP client not initialized');
      }

      const result = await executeGenerationPlan(this.client, plan, outputPath);
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      return {
        success: false,
        error: `Generation failed: ${errorMessage}`,
        log: [`Error: ${errorMessage}`]
      };
    }
  }

  stopBlender(): void {
    if (this.client) {
      this.client.disconnect();
      this.client = null;
    }
    if (this.blenderProcess) {
      this.blenderProcess.kill();
      this.blenderProcess = null;
    }
    this.isReady = false;
  }

  isBlenderReady(): boolean {
    return this.isReady && (this.client?.isConnected() ?? false);
  }
}

// Singleton instance
export const mcpManager = new MCPManager();
