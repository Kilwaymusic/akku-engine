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

  // ============================================================
  // CORE COMMANDS
  // ============================================================

  async getSceneInfo(): Promise<MCPResponse> {
    return this.sendCommand({ type: 'get_scene_info' });
  }

  async executeCode(code: string): Promise<MCPResponse> {
    return this.sendCommand({ type: 'execute_code', params: { code } });
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

  // Legacy commands (for backward compatibility)
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

  // ============================================================
  // AKKU SDK CATEGORY 1: BASE GENERATION
  // ============================================================

  /**
   * Spawn a clean topology humanoid base with optimized UV and proportions.
   * @param proportionType 'sd' | 'stylized' | 'realistic' | 'chibi'
   */
  async spawnHumanoidBase(proportionType: string = 'stylized'): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'spawn_humanoid_base',
      params: { proportion_type: proportionType }
    });
  }

  /**
   * Deform a specific body part using shape keys or scaling.
   * @param part 'head' | 'torso' | 'arms' | 'legs' | 'hands' | 'feet' | 'shoulders' | 'hips'
   * @param strength -1.0 to 1.0 (negative = shrink, positive = enlarge)
   * @param deformType 'scale' | 'stretch_vertical' | 'stretch_horizontal' | 'bulge'
   */
  async deformBody(part: string, strength: number = 0.5, deformType: string = 'scale'): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'deform_body',
      params: { part, strength, deform_type: deformType }
    });
  }

  // ============================================================
  // AKKU SDK CATEGORY 2: HARD-SURFACE KITBASHING
  // ============================================================

  /**
   * Attach armor plate at specified location.
   * @param location 'left_shoulder' | 'right_shoulder' | 'chest' | 'back' | 'left_knee' | 'right_knee' | etc.
   * @param style 'shoulder_pad' | 'chest_plate' | 'knee_guard' | 'gauntlet' | 'helmet_visor' | 'belt_buckle' | 'boot_plate'
   * @param scale Size multiplier
   */
  async attachArmorPlate(location: string, style: string = 'shoulder_pad', scale: number = 1.0): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'attach_armor_plate',
      params: { location, style, scale }
    });
  }

  /**
   * Add procedural sci-fi panel lines and details to an object.
   * @param targetObj Name of object to add details to
   * @param detailLevel 'low' | 'medium' | 'high'
   */
  async addScifiDetail(targetObj: string, detailLevel: string = 'medium'): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'add_scifi_detail',
      params: { target_obj: targetObj, detail_level: detailLevel }
    });
  }

  // ============================================================
  // AKKU SDK CATEGORY 3: GAME-READY PBR SHADING
  // ============================================================

  /**
   * Apply a PBR material preset to an object.
   * @param objectName Target object
   * @param presetName 'metal' | 'plastic' | 'cloth' | 'leather' | 'skin' | 'glow' | 'chrome' | 'gold' | 'rubber' | 'brushed_metal'
   * @param baseColor Optional [r, g, b] override (0-1 range)
   */
  async applyAkkuPBR(objectName: string, presetName: string, baseColor?: [number, number, number]): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'apply_akku_pbr',
      params: { object_name: objectName, preset_name: presetName, base_color: baseColor }
    });
  }

  /**
   * Fine-tune material properties on an object.
   * @param objectName Target object
   * @param metallic 0.0 - 1.0
   * @param roughness 0.0 - 1.0
   * @param emission Emission strength (0 = off)
   */
  async setMaterialProperty(objectName: string, metallic?: number, roughness?: number, emission?: number): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'set_material_property',
      params: { object_name: objectName, metallic, roughness, emission }
    });
  }

  // ============================================================
  // AKKU SDK CATEGORY 4: AUTO-RIG & ANIMATION
  // ============================================================

  /**
   * Join all mesh objects and bind to an armature with automatic weights.
   */
  async finalizeAndBind(): Promise<MCPResponse> {
    return this.sendCommand({ type: 'finalize_and_bind' });
  }

  /**
   * Apply a test animation clip to the character.
   * @param clipName 'idle' | 'walk' | 'attack' | 'jump'
   */
  async testAnimation(clipName: string = 'idle'): Promise<MCPResponse> {
    return this.sendCommand({
      type: 'test_animation',
      params: { clip_name: clipName }
    });
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

// ============================================================
// AKKU SDK STEP TYPES
// ============================================================

export type AkkuSDKAction = 
  // Category 1: Base Generation
  | 'spawn_humanoid_base'
  | 'deform_body'
  // Category 2: Hard-Surface Kitbashing  
  | 'attach_armor_plate'
  | 'add_scifi_detail'
  // Category 3: Game-Ready PBR Shading
  | 'apply_akku_pbr'
  | 'set_material_property'
  // Category 4: Auto-Rig & Animation
  | 'finalize_and_bind'
  | 'test_animation'
  // Legacy/Utility
  | 'export';

export interface AkkuGenerationStep {
  action: AkkuSDKAction;
  params: Record<string, any>;
  description: string;
}

export interface AkkuGenerationPlan {
  characterType: string;
  description: string;
  steps: AkkuGenerationStep[];
}

// Legacy types for backward compatibility
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

// ============================================================
// AKKU SDK EXECUTION ENGINE
// ============================================================

export async function executeAkkuPlan(
  client: BlenderMCPClient,
  plan: AkkuGenerationPlan,
  outputPath: string
): Promise<{ success: boolean; modelPath?: string; error?: string; log: string[] }> {
  const log: string[] = [];
  
  try {
    log.push(`Starting Akku SDK generation: ${plan.description}`);
    
    for (const step of plan.steps) {
      log.push(`Executing: ${step.description}`);
      
      let response: MCPResponse;
      
      switch (step.action) {
        // Category 1: Base Generation
        case 'spawn_humanoid_base':
          response = await client.spawnHumanoidBase(step.params.proportion_type);
          break;
        
        case 'deform_body':
          response = await client.deformBody(
            step.params.part,
            step.params.strength,
            step.params.deform_type
          );
          break;
        
        // Category 2: Hard-Surface Kitbashing
        case 'attach_armor_plate':
          response = await client.attachArmorPlate(
            step.params.location,
            step.params.style,
            step.params.scale
          );
          break;
        
        case 'add_scifi_detail':
          response = await client.addScifiDetail(
            step.params.target_obj,
            step.params.detail_level
          );
          break;
        
        // Category 3: Game-Ready PBR Shading
        case 'apply_akku_pbr':
          response = await client.applyAkkuPBR(
            step.params.object_name,
            step.params.preset_name,
            step.params.base_color
          );
          break;
        
        case 'set_material_property':
          response = await client.setMaterialProperty(
            step.params.object_name,
            step.params.metallic,
            step.params.roughness,
            step.params.emission
          );
          break;
        
        // Category 4: Auto-Rig & Animation
        case 'finalize_and_bind':
          response = await client.finalizeAndBind();
          break;
        
        case 'test_animation':
          response = await client.testAnimation(step.params.clip_name);
          break;
        
        // Export
        case 'export':
          response = await client.exportGLB(outputPath);
          break;
        
        default:
          throw new Error(`Unknown Akku SDK action: ${step.action}`);
      }
      
      if (response.status === 'error') {
        throw new Error(response.message || 'Unknown error');
      }
      
      log.push(`  Result: ${JSON.stringify(response.result).substring(0, 200)}`);
    }
    
    log.push('Akku SDK generation complete!');
    return { success: true, modelPath: outputPath, log };
    
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    log.push(`Error: ${errorMessage}`);
    return { success: false, error: errorMessage, log };
  }
}

// Legacy execution function (for backward compatibility)
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
