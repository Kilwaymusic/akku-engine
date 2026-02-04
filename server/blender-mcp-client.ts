import * as net from 'net';

export interface MCPCommand {
  type: string;
  params?: Record<string, any>;
}

export interface MCPResponse {
  status: 'success' | 'error';
  result?: any;
  message?: string;
}

export class BlenderMCPClient {
  private host: string;
  private port: number;
  private socket: net.Socket | null = null;
  private connected: boolean = false;
  private responseBuffer: string = '';

  constructor(host: string = 'localhost', port: number = 9876) {
    this.host = host;
    this.port = port;
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      this.socket = new net.Socket();
      
      this.socket.on('connect', () => {
        this.connected = true;
        console.log(`Connected to Blender MCP server at ${this.host}:${this.port}`);
        resolve();
      });

      this.socket.on('error', (err) => {
        console.error('MCP Socket error:', err.message);
        this.connected = false;
        reject(err);
      });

      this.socket.on('close', () => {
        this.connected = false;
        console.log('Disconnected from Blender MCP server');
      });

      this.socket.connect(this.port, this.host);
    });
  }

  async sendCommand(command: MCPCommand, timeout: number = 300000): Promise<MCPResponse> {
    if (!this.socket || !this.connected) {
      throw new Error('Not connected to MCP server');
    }

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('Command timeout'));
      }, timeout);

      const commandStr = JSON.stringify(command) + '\n';
      
      const onData = (data: Buffer) => {
        this.responseBuffer += data.toString();
        
        const newlineIndex = this.responseBuffer.indexOf('\n');
        if (newlineIndex !== -1) {
          const responseStr = this.responseBuffer.substring(0, newlineIndex);
          this.responseBuffer = this.responseBuffer.substring(newlineIndex + 1);
          
          clearTimeout(timeoutId);
          this.socket?.removeListener('data', onData);
          
          try {
            const response = JSON.parse(responseStr) as MCPResponse;
            resolve(response);
          } catch (e) {
            reject(new Error(`Invalid JSON response: ${responseStr}`));
          }
        }
      };

      this.socket!.on('data', onData);
      this.socket!.write(commandStr);
    });
  }

  async getSceneInfo(): Promise<MCPResponse> {
    return this.sendCommand({ type: 'get_scene_info' });
  }

  async executeCode(code: string): Promise<MCPResponse> {
    return this.sendCommand({ type: 'execute_code', params: { code } });
  }

  async createCharacter(characterType: string, params: Record<string, any>): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'create_character',
      params: { character_type: characterType, params }
    });
  }

  async applyModifier(objectName: string, modifierType: string, modifierParams?: Record<string, any>): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'apply_modifier',
      params: { 
        object_name: objectName, 
        modifier_type: modifierType, 
        params: modifierParams || {}
      }
    });
  }

  async setupMaterial(objectName: string, materialParams: Record<string, any>): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'setup_material',
      params: { 
        object_name: objectName, 
        material_params: materialParams 
      }
    });
  }

  async clearScene(): Promise<MCPResponse> {
    return this.sendCommand({ type: 'clear_scene' });
  }

  async exportGLB(filepath: string): Promise<MCPResponse> {
    return this.sendCommand({ type: 'export_glb', params: { filepath } });
  }

  async getObjectInfo(name: string): Promise<MCPResponse> {
    return this.sendCommand({ type: 'get_object_info', params: { name } });
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.destroy();
      this.socket = null;
      this.connected = false;
    }
  }

  isConnected(): boolean {
    return this.connected;
  }
}

export interface CharacterGenerationStep {
  action: 'create_base' | 'apply_modifier' | 'setup_material' | 'execute_code' | 'export';
  target?: string;
  params: Record<string, any>;
  description: string;
}

export interface CharacterGenerationPlan {
  characterType: string;
  description: string;
  steps: CharacterGenerationStep[];
}

export async function executeGenerationPlan(
  client: BlenderMCPClient,
  plan: CharacterGenerationPlan,
  outputPath: string
): Promise<{ success: boolean; modelPath?: string; error?: string; log: string[] }> {
  const log: string[] = [];
  
  try {
    log.push(`Starting generation: ${plan.description}`);
    
    for (const step of plan.steps) {
      log.push(`Executing: ${step.description}`);
      
      let response: MCPResponse;
      
      switch (step.action) {
        case 'create_base':
          response = await client.createCharacter(plan.characterType, step.params);
          break;
        
        case 'apply_modifier':
          if (!step.target) throw new Error('Modifier requires target object');
          // Extract modifier type and pass remaining params
          const modType = step.params.type as string;
          const modParams = { ...step.params };
          delete modParams.type;
          response = await client.applyModifier(step.target, modType, modParams);
          break;
        
        case 'setup_material':
          if (!step.target) throw new Error('Material setup requires target object');
          response = await client.setupMaterial(step.target, step.params);
          break;
        
        case 'execute_code':
          if (step.params.code) {
            response = await client.executeCode(step.params.code);
          } else {
            response = { status: 'success', result: 'No code to execute' };
          }
          break;
        
        case 'export':
          response = await client.exportGLB(outputPath);
          break;
        
        default:
          throw new Error(`Unknown action: ${step.action}`);
      }
      
      if (response.status === 'error') {
        throw new Error(response.message || 'Unknown error');
      }
      
      log.push(`  Result: ${JSON.stringify(response.result).substring(0, 200)}`);
    }
    
    log.push('Generation complete!');
    return { success: true, modelPath: outputPath, log };
    
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    log.push(`Error: ${errorMessage}`);
    return { success: false, error: errorMessage, log };
  }
}
