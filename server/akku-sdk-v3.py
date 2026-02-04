"""
Akku SDK v3.3 - Production-Ready Low-Poly Character Generation Toolkit
Features:
- MCP-style tool registry architecture
- Context-independent headless operations
- JSON error reporting system
- Step-by-step logging with mesh statistics
- Undo/rollback capability
- Boolean + Voxel Remesh workflow
- Body Type System with Lattice/Vertex deformation
"""

import bpy
import bmesh
import math
import sys
import os
import json
import re
import copy
import traceback
from datetime import datetime
from mathutils import Vector, Matrix
from typing import Dict, Any, Callable, Optional, Tuple, List, Union
from functools import wraps
from dataclasses import dataclass, asdict
from enum import Enum

# ========================================
# CONFIGURATION
# ========================================

class AkkuConfig:
    BASE_MESHES = {
        "male": "/home/composerkil/akku-engine/assets/base_meshes/Y_Bot.fbx",
        "female": "/home/composerkil/akku-engine/assets/base_meshes/X_Bot.fbx"
    }
    OUTPUT_DIR = "/home/composerkil/akku-engine/outputs"
    LOG_DIR = "/home/composerkil/akku-engine/logs"
    
    FBX_UNIT_SCALE = 0.01
    TARGET_HEIGHT = 1.8
    
    # Voxel Remesh settings
    VOXEL_SIZE_DEFAULT = 0.02
    SMOOTH_ITERATIONS = 2
    SMOOTH_FACTOR = 0.5


# ========================================
# ERROR HANDLING & LOGGING SYSTEM
# ========================================

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class MeshStats:
    """Mesh statistics snapshot"""
    vertex_count: int = 0
    face_count: int = 0
    triangle_count: int = 0
    edge_count: int = 0
    material_count: int = 0
    bounds_min: Tuple[float, float, float] = (0, 0, 0)
    bounds_max: Tuple[float, float, float] = (0, 0, 0)
    height: float = 0.0


@dataclass
class StepResult:
    """Result of a pipeline step"""
    step_name: str
    success: bool
    message: str
    mesh_stats: Optional[MeshStats] = None
    duration_ms: float = 0.0
    timestamp: str = ""
    error_details: Optional[Dict[str, Any]] = None


@dataclass
class ErrorReport:
    """Standardized JSON error report"""
    error_code: str
    error_type: str
    message: str
    step_name: str
    timestamp: str
    stack_trace: str
    mesh_state: Optional[MeshStats] = None
    recovery_attempted: bool = False
    recovery_success: bool = False


class AkkuLogger:
    """Centralized logging system with JSON output"""
    
    _instance = None
    _logs: List[Dict[str, Any]] = []
    _step_results: List[StepResult] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._logs = []
            cls._step_results = []
        return cls._instance
    
    @classmethod
    def log(cls, level: LogLevel, message: str, data: Dict[str, Any] = None):
        """Log a message with optional data"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.value,
            "message": message,
            "data": data or {}
        }
        cls._logs.append(entry)
        
        # Print to console
        prefix = f"[Akku SDK][{level.value}]"
        print(f"{prefix} {message}")
        if data:
            print(f"  Data: {json.dumps(data, indent=2, ensure_ascii=False, default=str)}")
    
    @classmethod
    def info(cls, message: str, data: Dict[str, Any] = None):
        cls.log(LogLevel.INFO, message, data)
    
    @classmethod
    def warning(cls, message: str, data: Dict[str, Any] = None):
        cls.log(LogLevel.WARNING, message, data)
    
    @classmethod
    def error(cls, message: str, data: Dict[str, Any] = None):
        cls.log(LogLevel.ERROR, message, data)
    
    @classmethod
    def debug(cls, message: str, data: Dict[str, Any] = None):
        cls.log(LogLevel.DEBUG, message, data)
    
    @classmethod
    def add_step_result(cls, result: StepResult):
        """Add a step result to the log"""
        cls._step_results.append(result)
        status = "SUCCESS" if result.success else "FAILED"
        cls.info(f"Step '{result.step_name}': {status}", {
            "duration_ms": result.duration_ms,
            "mesh_stats": asdict(result.mesh_stats) if result.mesh_stats else None
        })
    
    @classmethod
    def create_error_report(cls, exception: Exception, step_name: str, mesh_stats: MeshStats = None) -> ErrorReport:
        """Create a standardized error report from an exception"""
        return ErrorReport(
            error_code=type(exception).__name__,
            error_type=str(type(exception).__module__) + "." + type(exception).__name__,
            message=str(exception),
            step_name=step_name,
            timestamp=datetime.now().isoformat(),
            stack_trace=traceback.format_exc(),
            mesh_state=mesh_stats
        )
    
    @classmethod
    def get_json_report(cls) -> str:
        """Get full log as JSON string"""
        report = {
            "logs": cls._logs,
            "step_results": [asdict(r) for r in cls._step_results],
            "summary": {
                "total_steps": len(cls._step_results),
                "successful_steps": sum(1 for r in cls._step_results if r.success),
                "failed_steps": sum(1 for r in cls._step_results if not r.success)
            }
        }
        return json.dumps(report, indent=2, ensure_ascii=False, default=str)
    
    @classmethod
    def clear(cls):
        """Clear all logs"""
        cls._logs = []
        cls._step_results = []


# ========================================
# UNDO/SNAPSHOT SYSTEM
# ========================================

class MeshSnapshot:
    """Stores a snapshot of mesh data for undo operations"""
    
    def __init__(self, obj: bpy.types.Object):
        if obj.type != 'MESH':
            raise ValueError("Can only snapshot mesh objects")
        
        self.object_name = obj.name
        self.mesh_data = None
        self._capture(obj)
    
    def _capture(self, obj: bpy.types.Object):
        """Capture current mesh state"""
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        # Store vertex positions
        self.vertices = [(v.co.x, v.co.y, v.co.z) for v in bm.verts]
        
        # Store face indices
        bm.verts.ensure_lookup_table()
        self.faces = [[v.index for v in f.verts] for f in bm.faces]
        
        # Store materials
        self.materials = [slot.material.name if slot.material else None 
                         for slot in obj.material_slots]
        
        # Store transform
        self.location = tuple(obj.location)
        self.rotation = tuple(obj.rotation_euler)
        self.scale = tuple(obj.scale)
        
        bm.free()
        AkkuLogger.debug(f"Captured snapshot of '{obj.name}'", {
            "vertices": len(self.vertices),
            "faces": len(self.faces)
        })
    
    def restore(self) -> bool:
        """Restore mesh to snapshot state"""
        obj = bpy.data.objects.get(self.object_name)
        if not obj or obj.type != 'MESH':
            AkkuLogger.error(f"Cannot restore: object '{self.object_name}' not found")
            return False
        
        try:
            bm = bmesh.new()
            
            # Recreate vertices
            for co in self.vertices:
                bm.verts.new(Vector(co))
            
            bm.verts.ensure_lookup_table()
            
            # Recreate faces
            for face_indices in self.faces:
                try:
                    verts = [bm.verts[i] for i in face_indices]
                    bm.faces.new(verts)
                except:
                    pass
            
            # Apply to mesh
            obj.data.clear_geometry()
            bm.to_mesh(obj.data)
            bm.free()
            
            # Restore transform
            obj.location = Vector(self.location)
            obj.rotation_euler = self.rotation
            obj.scale = Vector(self.scale)
            
            obj.data.update()
            
            AkkuLogger.info(f"Restored snapshot of '{self.object_name}'")
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Failed to restore snapshot: {str(e)}")
            return False


class UndoManager:
    """Manages undo states for mesh operations"""
    
    _snapshots: Dict[str, List[MeshSnapshot]] = {}
    _max_history = 10
    
    @classmethod
    def save_state(cls, obj: bpy.types.Object, label: str = ""):
        """Save current state for potential undo"""
        if obj.type != 'MESH':
            return
        
        obj_name = obj.name
        if obj_name not in cls._snapshots:
            cls._snapshots[obj_name] = []
        
        snapshot = MeshSnapshot(obj)
        cls._snapshots[obj_name].append(snapshot)
        
        # Limit history size
        if len(cls._snapshots[obj_name]) > cls._max_history:
            cls._snapshots[obj_name].pop(0)
        
        AkkuLogger.debug(f"Saved undo state for '{obj_name}'", {"label": label})
    
    @classmethod
    def undo(cls, obj_name: str) -> bool:
        """Undo to previous state"""
        if obj_name not in cls._snapshots or not cls._snapshots[obj_name]:
            AkkuLogger.warning(f"No undo history for '{obj_name}'")
            return False
        
        snapshot = cls._snapshots[obj_name].pop()
        return snapshot.restore()
    
    @classmethod
    def clear(cls, obj_name: str = None):
        """Clear undo history"""
        if obj_name:
            cls._snapshots.pop(obj_name, None)
        else:
            cls._snapshots.clear()


# ========================================
# MESH STATISTICS
# ========================================

class MeshAnalyzer:
    """Analyzes mesh and provides statistics"""
    
    @staticmethod
    def get_stats(obj: bpy.types.Object) -> MeshStats:
        """Get comprehensive mesh statistics"""
        if obj.type != 'MESH':
            return MeshStats()
        
        mesh = obj.data
        
        # Get triangle count via bmesh
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tri_count = len(bm.faces)
        bm.free()
        
        # Get bounds
        bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        min_co = (min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox))
        max_co = (max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox))
        height = max_co[2] - min_co[2]
        
        return MeshStats(
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.polygons),
            triangle_count=tri_count,
            edge_count=len(mesh.edges),
            material_count=len(obj.material_slots),
            bounds_min=min_co,
            bounds_max=max_co,
            height=height
        )
    
    @staticmethod
    def log_stats(obj: bpy.types.Object, label: str = ""):
        """Log mesh statistics"""
        stats = MeshAnalyzer.get_stats(obj)
        AkkuLogger.info(f"Mesh Stats{' - ' + label if label else ''}", {
            "object": obj.name,
            "vertices": stats.vertex_count,
            "faces": stats.face_count,
            "triangles": stats.triangle_count,
            "height": f"{stats.height:.3f}m"
        })
        return stats


# ========================================
# TOOL REGISTRY WITH ERROR HANDLING
# ========================================

class ToolRegistry:
    """MCP-style tool registry with integrated error handling"""
    
    _tools: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, description: str = ""):
        """Decorator to register a tool function with error handling"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                import time
                start_time = time.time()
                
                AkkuLogger.info(f"Executing tool: {name}")
                
                try:
                    result = func(*args, **kwargs)
                    duration = (time.time() - start_time) * 1000
                    
                    # Get mesh stats if available
                    mesh_stats = None
                    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
                    if mesh_objects:
                        mesh_stats = MeshAnalyzer.get_stats(mesh_objects[0])
                    
                    step_result = StepResult(
                        step_name=name,
                        success=True,
                        message="Completed successfully",
                        mesh_stats=mesh_stats,
                        duration_ms=duration,
                        timestamp=datetime.now().isoformat()
                    )
                    AkkuLogger.add_step_result(step_result)
                    
                    return result
                    
                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    
                    # Get mesh stats for error context
                    mesh_stats = None
                    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
                    if mesh_objects:
                        mesh_stats = MeshAnalyzer.get_stats(mesh_objects[0])
                    
                    # Create error report
                    error_report = AkkuLogger.create_error_report(e, name, mesh_stats)
                    
                    step_result = StepResult(
                        step_name=name,
                        success=False,
                        message=str(e),
                        mesh_stats=mesh_stats,
                        duration_ms=duration,
                        timestamp=datetime.now().isoformat(),
                        error_details=asdict(error_report)
                    )
                    AkkuLogger.add_step_result(step_result)
                    
                    raise
            
            cls._tools[name] = {
                "function": wrapper,
                "description": description,
                "name": name
            }
            return wrapper
        return decorator
    
    @classmethod
    def execute(cls, tool_name: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a registered tool by name"""
        if tool_name not in cls._tools:
            return {"status": "error", "message": f"Tool '{tool_name}' not found"}
        
        try:
            result = cls._tools[tool_name]["function"](**(params or {}))
            return {"status": "success", "result": result}
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "error_report": asdict(AkkuLogger.create_error_report(e, tool_name))
            }
    
    @classmethod
    def list_tools(cls) -> List[Dict[str, str]]:
        """List all registered tools"""
        return [{"name": t["name"], "description": t["description"]} for t in cls._tools.values()]


# Shortcut decorator
tool = ToolRegistry.register


# ========================================
# COLOR & STYLE DETECTION
# ========================================

class StyleAnalyzer:
    """Analyzes prompts to extract style, colors, and archetypes"""
    
    COLORS = {
        "빨강": (1.0, 0.1, 0.1), "빨간": (1.0, 0.1, 0.1), "레드": (1.0, 0.1, 0.1),
        "파랑": (0.1, 0.3, 1.0), "파란": (0.1, 0.3, 1.0), "블루": (0.1, 0.3, 1.0),
        "초록": (0.1, 0.8, 0.2), "녹색": (0.1, 0.8, 0.2), "그린": (0.1, 0.8, 0.2),
        "노랑": (1.0, 0.9, 0.1), "노란": (1.0, 0.9, 0.1), "옐로우": (1.0, 0.9, 0.1),
        "주황": (1.0, 0.5, 0.0), "오렌지": (1.0, 0.5, 0.0),
        "보라": (0.6, 0.2, 0.8), "퍼플": (0.6, 0.2, 0.8),
        "분홍": (1.0, 0.5, 0.7), "핑크": (1.0, 0.5, 0.7),
        "검정": (0.05, 0.05, 0.05), "검은": (0.05, 0.05, 0.05), "블랙": (0.05, 0.05, 0.05),
        "흰": (0.95, 0.95, 0.95), "하얀": (0.95, 0.95, 0.95), "화이트": (0.95, 0.95, 0.95),
        "회색": (0.5, 0.5, 0.5), "그레이": (0.5, 0.5, 0.5),
        "금색": (0.9, 0.7, 0.2), "골드": (0.9, 0.7, 0.2),
        "은색": (0.8, 0.8, 0.85), "실버": (0.8, 0.8, 0.85),
        "갈색": (0.4, 0.25, 0.1), "브라운": (0.4, 0.25, 0.1),
        "청록": (0.0, 0.8, 0.8), "시안": (0.0, 0.8, 0.8),
        "메탈릭": (0.6, 0.6, 0.7),
        "red": (1.0, 0.1, 0.1), "blue": (0.1, 0.3, 1.0), "green": (0.1, 0.8, 0.2),
        "yellow": (1.0, 0.9, 0.1), "orange": (1.0, 0.5, 0.0), "purple": (0.6, 0.2, 0.8),
        "pink": (1.0, 0.5, 0.7), "black": (0.05, 0.05, 0.05), "white": (0.95, 0.95, 0.95),
        "gray": (0.5, 0.5, 0.5), "grey": (0.5, 0.5, 0.5), "gold": (0.9, 0.7, 0.2),
        "silver": (0.8, 0.8, 0.85), "brown": (0.4, 0.25, 0.1), "cyan": (0.0, 0.8, 0.8),
        "metallic": (0.6, 0.6, 0.7)
    }
    
    ARCHETYPES = {
        "robot": {"metallic": 0.9, "roughness": 0.2, "emission": 0.1},
        "로봇": {"metallic": 0.9, "roughness": 0.2, "emission": 0.1},
        "warrior": {"metallic": 0.7, "roughness": 0.3, "emission": 0.0},
        "전사": {"metallic": 0.7, "roughness": 0.3, "emission": 0.0},
        "wizard": {"metallic": 0.1, "roughness": 0.6, "emission": 0.3},
        "마법사": {"metallic": 0.1, "roughness": 0.6, "emission": 0.3},
        "knight": {"metallic": 0.85, "roughness": 0.25, "emission": 0.0},
        "기사": {"metallic": 0.85, "roughness": 0.25, "emission": 0.0},
        "ninja": {"metallic": 0.2, "roughness": 0.8, "emission": 0.0},
        "닌자": {"metallic": 0.2, "roughness": 0.8, "emission": 0.0},
        "zombie": {"metallic": 0.0, "roughness": 0.9, "emission": 0.0},
        "좀비": {"metallic": 0.0, "roughness": 0.9, "emission": 0.0},
        "cyborg": {"metallic": 0.8, "roughness": 0.3, "emission": 0.2},
        "사이보그": {"metallic": 0.8, "roughness": 0.3, "emission": 0.2},
        "elf": {"metallic": 0.1, "roughness": 0.5, "emission": 0.05},
        "엘프": {"metallic": 0.1, "roughness": 0.5, "emission": 0.05},
    }
    
    PROPORTION_TYPES = {
        "stylized": {"scale": 1.0},
        "chibi": {"scale": 0.6},
        "sd": {"scale": 0.65},
        "mobile": {"scale": 0.8},
        "minifig": {"scale": 0.5},
        "cartoon": {"scale": 0.85},
        "realistic": {"scale": 1.0}
    }
    
    POLY_LEVELS = {
        "ultra_low": {"decimate_ratio": 0.15, "max_tris": 300, "voxel_size": 0.04},
        "low": {"decimate_ratio": 0.3, "max_tris": 800, "voxel_size": 0.03},
        "medium": {"decimate_ratio": 0.5, "max_tris": 1500, "voxel_size": 0.02},
        "high": {"decimate_ratio": 0.75, "max_tris": 3000, "voxel_size": 0.015}
    }
    
    @classmethod
    def detect_color(cls, prompt: str) -> Tuple[float, float, float]:
        prompt_lower = prompt.lower()
        for keyword, color in cls.COLORS.items():
            if keyword in prompt_lower:
                return color
        return (0.5, 0.5, 0.6)
    
    @classmethod
    def detect_archetype(cls, prompt: str) -> Dict[str, float]:
        prompt_lower = prompt.lower()
        for keyword, props in cls.ARCHETYPES.items():
            if keyword in prompt_lower:
                return props
        return {"metallic": 0.3, "roughness": 0.5, "emission": 0.0}
    
    @classmethod
    def get_proportion_scale(cls, style: str) -> float:
        return cls.PROPORTION_TYPES.get(style, cls.PROPORTION_TYPES["stylized"])["scale"]
    
    @classmethod
    def get_poly_settings(cls, level: str) -> Dict[str, Any]:
        return cls.POLY_LEVELS.get(level, cls.POLY_LEVELS["medium"])


# ========================================
# CONTEXT-INDEPENDENT MESH OPERATIONS
# ========================================

class MeshTools:
    """Low-level mesh manipulation tools - Context Independent"""
    
    @staticmethod
    def clear_scene():
        """Clear all objects from scene"""
        while bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[0], do_unlink=True)
        
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        
        for mat in list(bpy.data.materials):
            if mat.users == 0:
                bpy.data.materials.remove(mat)
        
        for arm in list(bpy.data.armatures):
            if arm.users == 0:
                bpy.data.armatures.remove(arm)
        
        for action in list(bpy.data.actions):
            if action.users == 0:
                bpy.data.actions.remove(action)
        
        AkkuLogger.info("Scene cleared")
    
    @staticmethod
    def get_mesh_bounds(obj) -> Tuple[Vector, Vector, float]:
        """Get mesh bounding box and height"""
        if obj.type != 'MESH':
            return Vector((0, 0, 0)), Vector((0, 0, 0)), 0
        
        bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        min_co = Vector((min(v.x for v in bbox), min(v.y for v in bbox), min(v.z for v in bbox)))
        max_co = Vector((max(v.x for v in bbox), max(v.y for v in bbox), max(v.z for v in bbox)))
        height = max_co.z - min_co.z
        
        return min_co, max_co, height
    
    @staticmethod
    def normalize_scale(obj, target_height: float = 1.8):
        """Normalize object to target height using bmesh"""
        if obj.type != 'MESH':
            return 1.0
        
        # Save state for potential undo
        UndoManager.save_state(obj, "before_normalize")
        
        _, _, current_height = MeshTools.get_mesh_bounds(obj)
        
        if current_height > 0:
            scale_factor = target_height / current_height
            
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            bmesh.ops.scale(
                bm,
                vec=Vector((scale_factor, scale_factor, scale_factor)),
                space=Matrix.Identity(4),
                verts=bm.verts
            )
            
            bm.to_mesh(obj.data)
            bm.free()
            
            obj.scale = (1.0, 1.0, 1.0)
            obj.data.update()
            
            AkkuLogger.info(f"Normalized scale: {current_height:.2f}m -> {target_height:.2f}m", {
                "scale_factor": scale_factor
            })
            return scale_factor
        return 1.0
    
    @staticmethod
    def apply_modifier_via_depsgraph(obj, modifier_name: str):
        """Apply modifier using depsgraph - Context Independent"""
        if obj.type != 'MESH' or modifier_name not in obj.modifiers:
            return
        
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(depsgraph)
        mesh_eval = obj_eval.to_mesh()
        
        bm = bmesh.new()
        bm.from_mesh(mesh_eval)
        obj.data.clear_geometry()
        bm.to_mesh(obj.data)
        bm.free()
        
        obj_eval.to_mesh_clear()
        obj.modifiers.remove(obj.modifiers[modifier_name])
        obj.data.update()
    
    @staticmethod
    def decimate_mesh(obj, ratio: float):
        """Decimate mesh with modifier + depsgraph"""
        if obj.type != 'MESH':
            return
        
        UndoManager.save_state(obj, "before_decimate")
        
        mod = obj.modifiers.new(name="AkkuDecimate", type='DECIMATE')
        mod.ratio = max(0.1, min(1.0, ratio))
        mod.use_collapse_triangulate = True
        
        MeshTools.apply_modifier_via_depsgraph(obj, "AkkuDecimate")
        AkkuLogger.info(f"Applied decimation", {"ratio": ratio})
    
    @staticmethod
    def triangulate_mesh(obj):
        """Triangulate mesh using bmesh"""
        if obj.type != 'MESH':
            return
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        AkkuLogger.info("Mesh triangulated")
    
    @staticmethod
    def get_triangle_count(obj) -> int:
        """Get triangle count for mesh"""
        if obj.type != 'MESH':
            return 0
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tri_count = len(bm.faces)
        bm.free()
        
        return tri_count


# ========================================
# BOOLEAN + VOXEL REMESH WORKFLOW
# ========================================

class BooleanRemeshTools:
    """Advanced mesh operations: Boolean Union, Voxel Remesh, Smoothing"""
    
    @staticmethod
    def boolean_union(target_obj: bpy.types.Object, source_obj: bpy.types.Object) -> bool:
        """
        Perform Boolean Union operation using bmesh
        Merges source_obj into target_obj
        """
        if target_obj.type != 'MESH' or source_obj.type != 'MESH':
            AkkuLogger.error("Boolean union requires mesh objects")
            return False
        
        UndoManager.save_state(target_obj, "before_boolean_union")
        
        try:
            # Create modifier
            mod = target_obj.modifiers.new(name="AkkuBoolean", type='BOOLEAN')
            mod.operation = 'UNION'
            mod.object = source_obj
            mod.solver = 'FAST'  # FAST solver is more reliable for low-poly
            
            # Apply via depsgraph
            MeshTools.apply_modifier_via_depsgraph(target_obj, "AkkuBoolean")
            
            # Remove source object
            bpy.data.objects.remove(source_obj, do_unlink=True)
            
            AkkuLogger.info("Boolean union completed", {
                "target": target_obj.name
            })
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Boolean union failed: {str(e)}")
            UndoManager.undo(target_obj.name)
            return False
    
    @staticmethod
    def union_all_meshes() -> Optional[bpy.types.Object]:
        """
        Union all mesh objects in scene into a single mesh
        Returns the unified mesh object
        """
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        
        if len(mesh_objects) == 0:
            AkkuLogger.warning("No mesh objects to union")
            return None
        
        if len(mesh_objects) == 1:
            AkkuLogger.info("Only one mesh object, no union needed")
            return mesh_objects[0]
        
        # Use first mesh as target
        target = mesh_objects[0]
        UndoManager.save_state(target, "before_union_all")
        
        # Join all meshes using bmesh (context-independent)
        bm = bmesh.new()
        bm.from_mesh(target.data)
        
        for obj in mesh_objects[1:]:
            # Transform vertices to world space and add to bmesh
            temp_bm = bmesh.new()
            temp_bm.from_mesh(obj.data)
            
            # Transform to world coordinates
            for v in temp_bm.verts:
                v.co = obj.matrix_world @ v.co
            
            # Merge into main bmesh
            temp_bm.to_mesh(target.data)
            bm.from_mesh(target.data)
            temp_bm.free()
            
            # Remove source object
            bpy.data.objects.remove(obj, do_unlink=True)
        
        bm.to_mesh(target.data)
        bm.free()
        target.data.update()
        
        AkkuLogger.info("Unified all meshes", {
            "result_name": target.name,
            "original_count": len(mesh_objects)
        })
        
        return target
    
    @staticmethod
    def voxel_remesh(obj: bpy.types.Object, voxel_size: float = 0.02) -> bool:
        """
        Apply Voxel Remesh to create organic, connected geometry
        """
        if obj.type != 'MESH':
            AkkuLogger.error("Voxel remesh requires mesh object")
            return False
        
        UndoManager.save_state(obj, "before_voxel_remesh")
        
        try:
            # Add remesh modifier
            mod = obj.modifiers.new(name="AkkuRemesh", type='REMESH')
            mod.mode = 'VOXEL'
            mod.voxel_size = voxel_size
            mod.use_smooth_shade = False
            mod.adaptivity = 0.0
            
            # Apply via depsgraph
            MeshTools.apply_modifier_via_depsgraph(obj, "AkkuRemesh")
            
            stats = MeshAnalyzer.get_stats(obj)
            AkkuLogger.info("Voxel remesh completed", {
                "voxel_size": voxel_size,
                "new_vertex_count": stats.vertex_count,
                "new_face_count": stats.face_count
            })
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Voxel remesh failed: {str(e)}")
            UndoManager.undo(obj.name)
            return False
    
    @staticmethod
    def smooth_mesh(obj: bpy.types.Object, iterations: int = 2, factor: float = 0.5) -> bool:
        """
        Apply smoothing to create low-poly silhouette
        """
        if obj.type != 'MESH':
            return False
        
        UndoManager.save_state(obj, "before_smooth")
        
        try:
            # Use bmesh smooth
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            for _ in range(iterations):
                bmesh.ops.smooth_vert(
                    bm,
                    verts=bm.verts,
                    factor=factor,
                    use_axis_x=True,
                    use_axis_y=True,
                    use_axis_z=True
                )
            
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()
            
            AkkuLogger.info("Smoothing completed", {
                "iterations": iterations,
                "factor": factor
            })
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Smoothing failed: {str(e)}")
            UndoManager.undo(obj.name)
            return False
    
    @staticmethod
    def union_and_smooth(voxel_size: float = 0.02, smooth_iterations: int = 2) -> Optional[bpy.types.Object]:
        """
        Complete workflow: Union all parts -> Voxel Remesh -> Smooth
        Creates organic, connected low-poly character
        """
        AkkuLogger.info("Starting Union and Smooth workflow", {
            "voxel_size": voxel_size,
            "smooth_iterations": smooth_iterations
        })
        
        # Step 1: Union all meshes
        unified = BooleanRemeshTools.union_all_meshes()
        if not unified:
            return None
        
        MeshAnalyzer.log_stats(unified, "After Union")
        
        # Step 2: Voxel Remesh
        if not BooleanRemeshTools.voxel_remesh(unified, voxel_size):
            AkkuLogger.warning("Voxel remesh failed, continuing without")
        else:
            MeshAnalyzer.log_stats(unified, "After Voxel Remesh")
        
        # Step 3: Smooth
        if not BooleanRemeshTools.smooth_mesh(unified, smooth_iterations, 0.5):
            AkkuLogger.warning("Smoothing failed, continuing without")
        else:
            MeshAnalyzer.log_stats(unified, "After Smooth")
        
        AkkuLogger.info("Union and Smooth workflow completed")
        return unified


# ========================================
# BODY TYPE SYSTEM (Step 4)
# Lattice & Bone-based body deformation
# ========================================

@dataclass
class BodyTypeParams:
    """Body type parameters for character customization"""
    muscular: float = 0.0      # -1.0 (thin) to 1.0 (muscular)
    fat: float = 0.0           # -1.0 (thin) to 1.0 (fat)
    height: float = 0.0        # -1.0 (short) to 1.0 (tall)
    shoulder_width: float = 0.0  # -1.0 (narrow) to 1.0 (wide)
    hip_width: float = 0.0     # -1.0 (narrow) to 1.0 (wide)
    leg_length: float = 0.0    # -1.0 (short) to 1.0 (long)
    arm_length: float = 0.0    # -1.0 (short) to 1.0 (long)
    head_size: float = 0.0     # -1.0 (small) to 1.0 (large)


class BodyTypePresets:
    """Predefined body type configurations"""
    
    PRESETS: Dict[str, BodyTypeParams] = {
        "default": BodyTypeParams(),
        "muscular": BodyTypeParams(muscular=0.8, shoulder_width=0.5, fat=-0.2),
        "thin": BodyTypeParams(muscular=-0.6, fat=-0.5, shoulder_width=-0.3),
        "fat": BodyTypeParams(fat=0.7, muscular=-0.2, hip_width=0.4),
        "tall": BodyTypeParams(height=0.5, leg_length=0.3, arm_length=0.2),
        "short": BodyTypeParams(height=-0.4, leg_length=-0.2),
        "athletic": BodyTypeParams(muscular=0.5, fat=-0.3, shoulder_width=0.3, leg_length=0.1),
        "stocky": BodyTypeParams(height=-0.2, muscular=0.4, shoulder_width=0.4, fat=0.2),
        "slim": BodyTypeParams(muscular=-0.3, fat=-0.4, shoulder_width=-0.2, hip_width=-0.2),
        "heroic": BodyTypeParams(muscular=0.6, height=0.3, shoulder_width=0.5, hip_width=-0.1),
        "chibi": BodyTypeParams(height=-0.5, head_size=0.8, leg_length=-0.4, arm_length=-0.3),
        "giant": BodyTypeParams(height=0.8, muscular=0.4, shoulder_width=0.3),
    }
    
    # Korean aliases
    KOREAN_ALIASES: Dict[str, str] = {
        "근육질": "muscular",
        "마른": "thin",
        "뚱뚱한": "fat",
        "키큰": "tall",
        "키작은": "short",
        "운동선수": "athletic",
        "땅딸막한": "stocky",
        "날씬한": "slim",
        "영웅": "heroic",
        "치비": "chibi",
        "거인": "giant",
    }
    
    @classmethod
    def get_preset(cls, name: str) -> BodyTypeParams:
        """Get body type preset by name (supports Korean)"""
        # Check Korean aliases first
        if name in cls.KOREAN_ALIASES:
            name = cls.KOREAN_ALIASES[name]
        
        return cls.PRESETS.get(name.lower(), cls.PRESETS["default"])
    
    @classmethod
    def detect_from_prompt(cls, prompt: str) -> BodyTypeParams:
        """Detect body type from prompt text"""
        prompt_lower = prompt.lower()
        
        # Check for preset keywords
        for korean, english in cls.KOREAN_ALIASES.items():
            if korean in prompt_lower:
                AkkuLogger.info(f"Detected body type from prompt: {english}")
                return cls.get_preset(english)
        
        for preset_name in cls.PRESETS.keys():
            if preset_name in prompt_lower:
                AkkuLogger.info(f"Detected body type from prompt: {preset_name}")
                return cls.get_preset(preset_name)
        
        return cls.PRESETS["default"]


class BodyTypeSystem:
    """
    Body type deformation system using Lattice and vertex manipulation.
    Provides natural body shape changes instead of simple scaling.
    """
    
    # Body region definitions (approximate Z-height ranges for 1.8m character)
    BODY_REGIONS = {
        "head": {"z_min": 1.5, "z_max": 1.85, "scale_axes": "XYZ"},
        "neck": {"z_min": 1.4, "z_max": 1.5, "scale_axes": "XY"},
        "shoulders": {"z_min": 1.25, "z_max": 1.4, "scale_axes": "X"},
        "chest": {"z_min": 1.0, "z_max": 1.25, "scale_axes": "XYZ"},
        "waist": {"z_min": 0.85, "z_max": 1.0, "scale_axes": "XY"},
        "hips": {"z_min": 0.7, "z_max": 0.85, "scale_axes": "XY"},
        "upper_legs": {"z_min": 0.4, "z_max": 0.7, "scale_axes": "XYZ"},
        "lower_legs": {"z_min": 0.0, "z_max": 0.4, "scale_axes": "XYZ"},
    }
    
    # Arm detection: vertices far from center X axis
    ARM_X_THRESHOLD = 0.15  # meters from center
    ARM_Z_RANGE = (0.9, 1.4)  # Z height range for arms
    
    @classmethod
    def create_lattice_for_mesh(cls, obj: bpy.types.Object, resolution: Tuple[int, int, int] = (4, 4, 6)) -> bpy.types.Object:
        """
        Create a lattice object that encompasses the mesh.
        Returns the lattice object.
        """
        if obj.type != 'MESH':
            return None
        
        # Get mesh bounds
        min_co, max_co, _ = MeshTools.get_mesh_bounds(obj)
        
        # Create lattice with padding
        padding = 0.05
        size = (
            (max_co.x - min_co.x) + padding * 2,
            (max_co.y - min_co.y) + padding * 2,
            (max_co.z - min_co.z) + padding * 2
        )
        center = (
            (min_co.x + max_co.x) / 2,
            (min_co.y + max_co.y) / 2,
            (min_co.z + max_co.z) / 2
        )
        
        # Create lattice data
        lattice_data = bpy.data.lattices.new(name="AkkuBodyLattice")
        lattice_data.points_u = resolution[0]
        lattice_data.points_v = resolution[1]
        lattice_data.points_w = resolution[2]
        lattice_data.interpolation_type_u = 'KEY_BSPLINE'
        lattice_data.interpolation_type_v = 'KEY_BSPLINE'
        lattice_data.interpolation_type_w = 'KEY_BSPLINE'
        
        # Create lattice object
        lattice_obj = bpy.data.objects.new("AkkuBodyLattice", lattice_data)
        bpy.context.collection.objects.link(lattice_obj)
        
        # Position and scale lattice
        lattice_obj.location = Vector(center)
        lattice_obj.scale = Vector(size)
        
        # Add lattice modifier to mesh
        mod = obj.modifiers.new(name="AkkuLattice", type='LATTICE')
        mod.object = lattice_obj
        
        AkkuLogger.info("Created lattice for body deformation", {
            "resolution": resolution,
            "size": size
        })
        
        return lattice_obj
    
    @classmethod
    def deform_lattice(cls, lattice_obj: bpy.types.Object, params: BodyTypeParams) -> bool:
        """
        Deform lattice points based on body type parameters.
        """
        if lattice_obj.type != 'LATTICE':
            return False
        
        lattice = lattice_obj.data
        points_u = lattice.points_u
        points_v = lattice.points_v
        points_w = lattice.points_w
        
        AkkuLogger.info("Deforming lattice", {
            "muscular": params.muscular,
            "fat": params.fat,
            "height": params.height
        })
        
        # Iterate through lattice points
        for i, point in enumerate(lattice.points):
            # Calculate grid position (normalized 0-1)
            w_idx = i // (points_u * points_v)
            remaining = i % (points_u * points_v)
            v_idx = remaining // points_u
            u_idx = remaining % points_u
            
            # Normalized positions
            u_norm = u_idx / max(1, points_u - 1)  # X axis
            v_norm = v_idx / max(1, points_v - 1)  # Y axis  
            w_norm = w_idx / max(1, points_w - 1)  # Z axis (height)
            
            # Calculate deformation
            dx, dy, dz = 0.0, 0.0, 0.0
            
            # Height deformation (stretch/compress along Z)
            if params.height != 0:
                # Scale from bottom, more effect on upper body
                dz = params.height * 0.15 * w_norm
            
            # Muscular/Fat affects X and Y (width)
            body_width_factor = params.muscular * 0.12 + params.fat * 0.15
            
            # Chest/shoulder region (upper body)
            if 0.55 < w_norm < 0.8:
                shoulder_factor = params.shoulder_width * 0.1
                dx = (u_norm - 0.5) * (body_width_factor + shoulder_factor)
                dy = (v_norm - 0.5) * body_width_factor * 0.7
            
            # Waist region (middle)
            elif 0.45 < w_norm <= 0.55:
                # Muscular = narrow waist, Fat = wide waist
                waist_factor = -params.muscular * 0.05 + params.fat * 0.1
                dx = (u_norm - 0.5) * waist_factor
                dy = (v_norm - 0.5) * waist_factor
            
            # Hip region
            elif 0.35 < w_norm <= 0.45:
                hip_factor = params.hip_width * 0.08 + params.fat * 0.08
                dx = (u_norm - 0.5) * hip_factor
                dy = (v_norm - 0.5) * hip_factor
            
            # Leg region
            elif w_norm <= 0.35:
                leg_scale = params.leg_length * 0.1
                dz = leg_scale * w_norm
                # Thicker legs for muscular/fat
                leg_width = (params.muscular * 0.05 + params.fat * 0.06) * (1 - w_norm)
                dx = (u_norm - 0.5) * leg_width
                dy = (v_norm - 0.5) * leg_width
            
            # Head region
            elif w_norm > 0.85:
                head_scale = params.head_size * 0.08
                dx = (u_norm - 0.5) * head_scale
                dy = (v_norm - 0.5) * head_scale
                dz += head_scale * 0.5
            
            # Apply deformation
            point.co_deform.x += dx
            point.co_deform.y += dy
            point.co_deform.z += dz
        
        return True
    
    @classmethod
    def apply_body_type_direct(cls, obj: bpy.types.Object, params: BodyTypeParams) -> bool:
        """
        Apply body type deformation directly to mesh vertices.
        More efficient than lattice for simple deformations.
        Context-independent using bmesh.
        """
        if obj.type != 'MESH':
            return False
        
        UndoManager.save_state(obj, "before_body_type")
        
        try:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            
            # Get mesh bounds for normalization
            z_coords = [v.co.z for v in bm.verts]
            z_min, z_max = min(z_coords), max(z_coords)
            height = z_max - z_min
            
            if height <= 0:
                bm.free()
                return False
            
            AkkuLogger.info("Applying body type directly", {
                "mesh_height": height,
                "params": asdict(params)
            })
            
            for vert in bm.verts:
                # Normalized height (0 = feet, 1 = head)
                z_norm = (vert.co.z - z_min) / height
                
                # Distance from center (for arms detection)
                x_dist = abs(vert.co.x)
                
                dx, dy, dz = 0.0, 0.0, 0.0
                
                # Height scaling
                if params.height != 0:
                    dz = params.height * 0.15 * height * z_norm
                
                # Body regions
                if z_norm > 0.85:  # Head
                    scale = 1.0 + params.head_size * 0.15
                    vert.co.x *= scale
                    vert.co.y *= scale
                    dz += params.head_size * 0.05 * height
                    
                elif 0.7 < z_norm <= 0.85:  # Shoulders/Upper chest
                    shoulder_scale = 1.0 + params.shoulder_width * 0.12 + params.muscular * 0.08
                    vert.co.x *= shoulder_scale
                    vert.co.y *= 1.0 + params.muscular * 0.05 + params.fat * 0.06
                    
                elif 0.55 < z_norm <= 0.7:  # Chest
                    chest_scale = 1.0 + params.muscular * 0.1 + params.fat * 0.08
                    vert.co.x *= chest_scale
                    vert.co.y *= chest_scale
                    
                elif 0.45 < z_norm <= 0.55:  # Waist
                    # Muscular = V-shape (narrow waist), Fat = wide waist
                    waist_scale = 1.0 - params.muscular * 0.08 + params.fat * 0.12
                    vert.co.x *= waist_scale
                    vert.co.y *= waist_scale
                    
                elif 0.35 < z_norm <= 0.45:  # Hips
                    hip_scale = 1.0 + params.hip_width * 0.1 + params.fat * 0.08
                    vert.co.x *= hip_scale
                    vert.co.y *= hip_scale
                    
                elif z_norm <= 0.35:  # Legs
                    # Leg length
                    if params.leg_length != 0:
                        leg_factor = 1.0 + params.leg_length * 0.15
                        vert.co.z = z_min + (vert.co.z - z_min) * leg_factor
                    
                    # Leg thickness
                    leg_thickness = 1.0 + params.muscular * 0.06 + params.fat * 0.08
                    vert.co.x *= leg_thickness
                    vert.co.y *= leg_thickness
                
                # Arm deformation (vertices far from center)
                if x_dist > 0.1 and 0.5 < z_norm < 0.8:
                    # Arm length
                    if params.arm_length != 0:
                        arm_extend = params.arm_length * 0.1 * height
                        if vert.co.x > 0:
                            vert.co.x += arm_extend * 0.3
                        else:
                            vert.co.x -= arm_extend * 0.3
                    
                    # Arm thickness
                    arm_scale = 1.0 + params.muscular * 0.12 + params.fat * 0.06
                    # Scale perpendicular to arm direction
                    vert.co.y *= arm_scale
                
                # Apply height change
                vert.co.z += dz
            
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()
            
            AkkuLogger.info("Body type deformation completed")
            MeshAnalyzer.log_stats(obj, "After body type")
            
            return True
            
        except Exception as e:
            AkkuLogger.error(f"Body type deformation failed: {str(e)}")
            UndoManager.undo(obj.name)
            return False
    
    @classmethod
    def apply_body_type(cls, obj: bpy.types.Object, params: BodyTypeParams, use_lattice: bool = False) -> bool:
        """
        Apply body type deformation to mesh.
        
        Args:
            obj: Target mesh object
            params: Body type parameters
            use_lattice: If True, use lattice deformation (smoother but requires modifier apply)
        """
        if use_lattice:
            # Create and deform lattice
            lattice = cls.create_lattice_for_mesh(obj, resolution=(4, 4, 8))
            if lattice:
                cls.deform_lattice(lattice, params)
                # Apply lattice modifier
                MeshTools.apply_modifier_via_depsgraph(obj, "AkkuLattice")
                # Remove lattice object
                bpy.data.objects.remove(lattice, do_unlink=True)
                return True
            return False
        else:
            # Direct vertex manipulation (faster, context-independent)
            return cls.apply_body_type_direct(obj, params)


# ========================================
# MATERIAL SYSTEM
# ========================================

class MaterialSystem:
    """PBR Material creation system"""
    
    @staticmethod
    def create_material(
        name: str,
        color: Tuple[float, float, float],
        metallic: float = 0.0,
        roughness: float = 0.5,
        emission: float = 0.0
    ) -> bpy.types.Material:
        """Create a PBR material"""
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (400, 0)
        
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (0, 0)
        
        principled.inputs['Base Color'].default_value = (*color, 1.0)
        principled.inputs['Metallic'].default_value = metallic
        principled.inputs['Roughness'].default_value = roughness
        
        if emission > 0:
            for emission_input in ['Emission', 'Emission Color']:
                try:
                    principled.inputs[emission_input].default_value = (*color, 1.0)
                    break
                except KeyError:
                    continue
            
            try:
                principled.inputs['Emission Strength'].default_value = emission * 2.0
            except KeyError:
                pass
        
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        return mat
    
    @staticmethod
    def apply_material(obj, material: bpy.types.Material):
        """Apply material to object"""
        if obj.type != 'MESH':
            return
        
        obj.data.materials.clear()
        obj.data.materials.append(material)


# ========================================
# STYLIZED SHADER SYSTEM (Category 3)
# ========================================

@dataclass
class StylizedShaderParams:
    """Parameters for stylized low-poly shader"""
    base_color: Tuple[float, float, float] = (0.8, 0.2, 0.2)  # Base color
    edge_brightness: float = 0.3       # Edge highlight intensity (0-1)
    cavity_darkness: float = 0.4       # Cavity darkening intensity (0-1)
    ao_distance: float = 0.5           # Ambient Occlusion distance
    metallic: float = 0.0              # Metallic value
    roughness: float = 0.6             # Roughness value
    emission_strength: float = 0.0     # Emission strength
    use_fresnel: bool = True           # Add fresnel rim light
    fresnel_strength: float = 0.2      # Fresnel intensity


class StylizedShaderSystem:
    """
    Akku Stylized Shader System
    
    Creates procedural materials optimized for low-poly characters:
    - Edge highlighting using Geometry (Pointiness) node
    - Cavity darkening using Ambient Occlusion
    - Optional fresnel rim lighting
    - PBR compatible for game engines
    """
    
    @staticmethod
    def create_stylized_material(
        name: str,
        params: StylizedShaderParams = None
    ) -> bpy.types.Material:
        """
        Create Akku_Stylized_Shader material
        
        Node graph structure:
        - Geometry (Pointiness) -> ColorRamp -> Mix for edge highlighting
        - Ambient Occlusion -> ColorRamp -> Mix for cavity darkening
        - Fresnel -> Mix for rim lighting (optional)
        - All mixed into Principled BSDF
        """
        if params is None:
            params = StylizedShaderParams()
        
        mat_name = f"Akku_Stylized_{name}"
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        
        # ===== OUTPUT NODE =====
        output = nodes.new('ShaderNodeOutputMaterial')
        output.location = (800, 0)
        
        # ===== PRINCIPLED BSDF =====
        principled = nodes.new('ShaderNodeBsdfPrincipled')
        principled.location = (500, 0)
        principled.inputs['Metallic'].default_value = params.metallic
        principled.inputs['Roughness'].default_value = params.roughness
        
        if params.emission_strength > 0:
            for emission_input in ['Emission', 'Emission Color']:
                try:
                    principled.inputs[emission_input].default_value = (*params.base_color, 1.0)
                    break
                except KeyError:
                    continue
            try:
                principled.inputs['Emission Strength'].default_value = params.emission_strength
            except KeyError:
                pass
        
        links.new(principled.outputs['BSDF'], output.inputs['Surface'])
        
        # ===== BASE COLOR =====
        base_color_node = nodes.new('ShaderNodeRGB')
        base_color_node.location = (-600, 200)
        base_color_node.outputs[0].default_value = (*params.base_color, 1.0)
        base_color_node.label = "Base Color"
        
        # ===== EDGE HIGHLIGHTING (Geometry Pointiness) =====
        geometry = nodes.new('ShaderNodeNewGeometry')
        geometry.location = (-600, -100)
        
        # Pointiness ColorRamp - converts pointiness to edge mask
        edge_ramp = nodes.new('ShaderNodeValToRGB')
        edge_ramp.location = (-400, -100)
        edge_ramp.label = "Edge Ramp"
        edge_ramp.color_ramp.elements[0].position = 0.4
        edge_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        edge_ramp.color_ramp.elements[1].position = 0.6
        edge_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        
        links.new(geometry.outputs['Pointiness'], edge_ramp.inputs['Fac'])
        
        # Edge highlight color (brighter version of base color)
        edge_color = nodes.new('ShaderNodeRGB')
        edge_color.location = (-400, 50)
        bright_factor = 1.0 + params.edge_brightness
        edge_color.outputs[0].default_value = (
            min(1.0, params.base_color[0] * bright_factor),
            min(1.0, params.base_color[1] * bright_factor),
            min(1.0, params.base_color[2] * bright_factor),
            1.0
        )
        edge_color.label = "Edge Highlight"
        
        # Mix base with edge highlight
        edge_mix = nodes.new('ShaderNodeMixRGB')
        edge_mix.location = (-200, 100)
        edge_mix.blend_type = 'MIX'
        edge_mix.label = "Edge Mix"
        
        links.new(edge_ramp.outputs['Color'], edge_mix.inputs['Fac'])
        links.new(base_color_node.outputs[0], edge_mix.inputs['Color1'])
        links.new(edge_color.outputs[0], edge_mix.inputs['Color2'])
        
        # ===== CAVITY DARKENING (Ambient Occlusion) =====
        ao = nodes.new('ShaderNodeAmbientOcclusion')
        ao.location = (-600, -350)
        ao.inputs['Distance'].default_value = params.ao_distance
        ao.samples = 16
        
        # AO ColorRamp - converts AO to cavity mask
        ao_ramp = nodes.new('ShaderNodeValToRGB')
        ao_ramp.location = (-400, -350)
        ao_ramp.label = "Cavity Ramp"
        ao_ramp.color_ramp.elements[0].position = 0.0
        ao_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        ao_ramp.color_ramp.elements[1].position = 0.8
        ao_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        
        links.new(ao.outputs['AO'], ao_ramp.inputs['Fac'])
        
        # Cavity color (darker version of base color)
        cavity_color = nodes.new('ShaderNodeRGB')
        cavity_color.location = (-400, -200)
        dark_factor = 1.0 - params.cavity_darkness
        cavity_color.outputs[0].default_value = (
            params.base_color[0] * dark_factor,
            params.base_color[1] * dark_factor,
            params.base_color[2] * dark_factor,
            1.0
        )
        cavity_color.label = "Cavity Dark"
        
        # Mix edge result with cavity darkening
        cavity_mix = nodes.new('ShaderNodeMixRGB')
        cavity_mix.location = (0, 0)
        cavity_mix.blend_type = 'MIX'
        cavity_mix.label = "Cavity Mix"
        
        links.new(ao_ramp.outputs['Color'], cavity_mix.inputs['Fac'])
        links.new(cavity_color.outputs[0], cavity_mix.inputs['Color1'])
        links.new(edge_mix.outputs['Color'], cavity_mix.inputs['Color2'])
        
        # ===== FRESNEL RIM LIGHT (Optional) =====
        if params.use_fresnel and params.fresnel_strength > 0:
            fresnel = nodes.new('ShaderNodeFresnel')
            fresnel.location = (-200, -200)
            fresnel.inputs['IOR'].default_value = 1.45
            
            # Rim color (slightly brighter and shifted)
            rim_color = nodes.new('ShaderNodeRGB')
            rim_color.location = (0, -350)
            rim_color.outputs[0].default_value = (
                min(1.0, params.base_color[0] + 0.2),
                min(1.0, params.base_color[1] + 0.2),
                min(1.0, params.base_color[2] + 0.2),
                1.0
            )
            rim_color.label = "Rim Color"
            
            # Multiply fresnel with rim color for colored rim effect
            rim_multiply = nodes.new('ShaderNodeMixRGB')
            rim_multiply.location = (100, -280)
            rim_multiply.blend_type = 'MULTIPLY'
            rim_multiply.inputs['Fac'].default_value = 1.0
            rim_multiply.label = "Rim Multiply"
            
            links.new(fresnel.outputs['Fac'], rim_multiply.inputs['Color1'])
            links.new(rim_color.outputs[0], rim_multiply.inputs['Color2'])
            
            # Final mix with fresnel (add rim to base)
            final_mix = nodes.new('ShaderNodeMixRGB')
            final_mix.location = (250, 0)
            final_mix.blend_type = 'ADD'
            final_mix.inputs['Fac'].default_value = params.fresnel_strength
            final_mix.label = "Fresnel Mix"
            
            links.new(cavity_mix.outputs['Color'], final_mix.inputs['Color1'])
            links.new(rim_multiply.outputs['Color'], final_mix.inputs['Color2'])
            
            links.new(final_mix.outputs['Color'], principled.inputs['Base Color'])
        else:
            links.new(cavity_mix.outputs['Color'], principled.inputs['Base Color'])
        
        AkkuLogger.info(f"Created stylized material: {mat_name}", {
            "edge_brightness": params.edge_brightness,
            "cavity_darkness": params.cavity_darkness,
            "use_fresnel": params.use_fresnel
        })
        
        return mat
    
    @staticmethod
    def apply_stylized_shader(
        obj,
        color: Tuple[float, float, float],
        style: str = "stylized"
    ) -> bpy.types.Material:
        """
        Apply stylized shader to object based on style preset
        
        Style presets:
        - stylized: Balanced edge/cavity (default)
        - chibi: Softer shadows, more edge highlight
        - heroic: Strong edge definition
        - cartoon: High contrast, minimal AO
        - realistic: Subtle effects
        """
        style_presets = {
            "stylized": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.3,
                cavity_darkness=0.35,
                fresnel_strength=0.15
            ),
            "chibi": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.4,
                cavity_darkness=0.2,
                ao_distance=0.3,
                fresnel_strength=0.25,
                roughness=0.7
            ),
            "sd": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.35,
                cavity_darkness=0.25,
                fresnel_strength=0.2
            ),
            "heroic": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.45,
                cavity_darkness=0.4,
                ao_distance=0.6,
                fresnel_strength=0.2,
                roughness=0.5
            ),
            "cartoon": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.5,
                cavity_darkness=0.15,
                ao_distance=0.3,
                use_fresnel=False,
                roughness=0.8
            ),
            "realistic": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.15,
                cavity_darkness=0.25,
                ao_distance=0.4,
                fresnel_strength=0.1,
                roughness=0.55
            ),
            "mobile": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.2,
                cavity_darkness=0.2,
                use_fresnel=False,
                roughness=0.7
            ),
            "minifig": StylizedShaderParams(
                base_color=color,
                edge_brightness=0.35,
                cavity_darkness=0.3,
                ao_distance=0.25,
                fresnel_strength=0.1,
                roughness=0.65
            )
        }
        
        params = style_presets.get(style, style_presets["stylized"])
        params.base_color = color  # Ensure color is applied
        
        mat = StylizedShaderSystem.create_stylized_material(obj.name, params)
        
        if obj.type == 'MESH':
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            AkkuLogger.info(f"Applied stylized shader to {obj.name}", {"style": style})
        
        return mat


# Register shader tool
@tool("apply_stylized_shader", "Apply Akku Stylized Shader with edge highlighting and cavity darkening")
def tool_apply_stylized_shader(params: Dict) -> Dict:
    """
    Apply stylized shader to character mesh
    
    Params:
        object_name: Name of object to apply shader to
        color: RGB tuple (0-1 range)
        style: Shader style preset (stylized, chibi, heroic, cartoon, realistic)
    """
    obj_name = params.get("object_name")
    color = tuple(params.get("color", (0.8, 0.2, 0.2)))
    style = params.get("style", "stylized")
    
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return {"status": "error", "message": f"Object not found: {obj_name}"}
    
    material = StylizedShaderSystem.apply_stylized_shader(obj, color, style)
    
    return {
        "status": "success",
        "material_name": material.name,
        "style": style,
        "color": color
    }


# ========================================
# FBX & GLB HANDLERS
# ========================================

class FBXHandler:
    @staticmethod
    def import_fbx(filepath: str) -> List[bpy.types.Object]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"FBX file not found: {filepath}")
        
        existing_objects = set(bpy.data.objects.keys())
        
        bpy.ops.import_scene.fbx(
            filepath=filepath,
            use_custom_normals=True,
            use_image_search=False,
            ignore_leaf_bones=True,
            automatic_bone_orientation=True,
            global_scale=1.0
        )
        
        new_objects = [obj for obj in bpy.data.objects if obj.name not in existing_objects]
        AkkuLogger.info(f"Imported FBX: {filepath}", {"new_objects": len(new_objects)})
        
        return new_objects


class GLBHandler:
    @staticmethod
    def export_glb(filepath: str) -> bool:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        bpy.ops.export_scene.gltf(
            filepath=filepath,
            export_format='GLB',
            use_selection=False,
            export_apply=True,
            export_animations=True,
            export_skins=True,
            export_morph=False,
            export_lights=False,
            export_cameras=False
        )
        
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            AkkuLogger.info(f"Exported GLB", {"path": filepath, "size": file_size})
            return True
        return False


# ========================================
# REGISTERED TOOLS
# ========================================

@tool("load_base_mesh", "Load Mixamo FBX base mesh")
def load_base_mesh(gender: str = "male") -> Dict[str, Any]:
    """Load and normalize a Mixamo FBX base mesh"""
    MeshTools.clear_scene()
    AkkuLogger.clear()
    
    mesh_path = AkkuConfig.BASE_MESHES.get(gender, AkkuConfig.BASE_MESHES["male"])
    new_objects = FBXHandler.import_fbx(mesh_path)
    
    mesh_objects = [obj for obj in new_objects if obj.type == 'MESH']
    
    if not mesh_objects:
        raise RuntimeError("No mesh objects found in FBX file")
    
    for obj in mesh_objects:
        MeshTools.normalize_scale(obj, AkkuConfig.TARGET_HEIGHT)
        MeshAnalyzer.log_stats(obj, "After normalization")
    
    return {
        "mesh_count": len(mesh_objects),
        "mesh_names": [obj.name for obj in mesh_objects],
        "target_height": AkkuConfig.TARGET_HEIGHT
    }


@tool("apply_style", "Apply style-based transformations")
def apply_style(prompt: str, style: str = "stylized", poly_level: str = "medium") -> Dict[str, Any]:
    """Apply style transformations based on prompt analysis"""
    
    color = StyleAnalyzer.detect_color(prompt)
    archetype = StyleAnalyzer.detect_archetype(prompt)
    proportion_scale = StyleAnalyzer.get_proportion_scale(style)
    poly_settings = StyleAnalyzer.get_poly_settings(poly_level)
    
    AkkuLogger.info("Style Analysis", {
        "color": color,
        "archetype": archetype,
        "proportion_scale": proportion_scale,
        "poly_level": poly_level
    })
    
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    
    for obj in mesh_objects:
        # Apply Stylized Shader with edge highlighting and cavity darkening
        StylizedShaderSystem.apply_stylized_shader(obj, color, style)
        
        if proportion_scale != 1.0:
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            bmesh.ops.scale(
                bm,
                vec=Vector((proportion_scale, proportion_scale, proportion_scale)),
                space=Matrix.Identity(4),
                verts=bm.verts
            )
            bm.to_mesh(obj.data)
            bm.free()
            obj.data.update()
        
        MeshTools.decimate_mesh(obj, poly_settings["decimate_ratio"])
        MeshTools.triangulate_mesh(obj)
    
    total_tris = sum(MeshTools.get_triangle_count(obj) for obj in mesh_objects)
    
    return {
        "color": color,
        "archetype": archetype,
        "proportion_scale": proportion_scale,
        "decimate_ratio": poly_settings["decimate_ratio"],
        "total_triangles": total_tris
    }


@tool("apply_body_type", "Apply body type deformation to character mesh")
def apply_body_type_tool(
    body_type: str = "default",
    muscular: float = None,
    fat: float = None,
    height: float = None,
    shoulder_width: float = None,
    hip_width: float = None,
    use_lattice: bool = False
) -> Dict[str, Any]:
    """
    Apply body type deformation to all mesh objects.
    
    Args:
        body_type: Preset name (muscular, thin, fat, tall, athletic, chibi, etc.)
        muscular/fat/height/etc: Override individual parameters (-1.0 to 1.0)
        use_lattice: Use lattice deformation (smoother but slower)
    """
    # Get preset or default
    params = BodyTypePresets.get_preset(body_type)
    
    # Override with individual parameters if provided
    if muscular is not None:
        params.muscular = muscular
    if fat is not None:
        params.fat = fat
    if height is not None:
        params.height = height
    if shoulder_width is not None:
        params.shoulder_width = shoulder_width
    if hip_width is not None:
        params.hip_width = hip_width
    
    AkkuLogger.info("Applying body type", {
        "preset": body_type,
        "params": asdict(params)
    })
    
    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
    success_count = 0
    
    for obj in mesh_objects:
        if BodyTypeSystem.apply_body_type(obj, params, use_lattice):
            success_count += 1
    
    return {
        "success": success_count > 0,
        "body_type": body_type,
        "params": asdict(params),
        "meshes_modified": success_count
    }


@tool("union_and_smooth", "Apply Boolean Union + Voxel Remesh + Smooth workflow")
def union_and_smooth_tool(voxel_size: float = 0.02, smooth_iterations: int = 2) -> Dict[str, Any]:
    """Combine all meshes with organic smoothing for low-poly style"""
    
    result = BooleanRemeshTools.union_and_smooth(voxel_size, smooth_iterations)
    
    if result:
        stats = MeshAnalyzer.get_stats(result)
        return {
            "success": True,
            "result_object": result.name,
            "vertex_count": stats.vertex_count,
            "face_count": stats.face_count,
            "triangle_count": stats.triangle_count
        }
    else:
        return {"success": False, "message": "Union and smooth failed"}


@tool("export_glb", "Export scene as GLB file")
def export_glb(output_path: str) -> Dict[str, Any]:
    """Export scene to GLB format"""
    success = GLBHandler.export_glb(output_path)
    
    if success:
        file_size = os.path.getsize(output_path)
        return {
            "path": output_path,
            "size_bytes": file_size,
            "success": True,
            "log_report": AkkuLogger.get_json_report()
        }
    else:
        raise RuntimeError(f"GLB export failed: {output_path}")


@tool("generate_character", "Complete character generation pipeline")
def generate_character(
    prompt: str,
    style: str = "stylized",
    poly_level: str = "medium",
    output_path: str = None,
    gender: str = "male",
    body_type: str = "auto",
    use_remesh: bool = False
) -> Dict[str, Any]:
    """
    Generate a complete low-poly character from prompt.
    
    Args:
        prompt: Character description (supports Korean)
        style: Proportion style (stylized, chibi, sd, mobile, minifig, cartoon, realistic)
        poly_level: Polygon detail (ultra_low, low, medium, high)
        output_path: GLB output file path
        gender: Base mesh gender (male, female)
        body_type: Body type preset or "auto" to detect from prompt
        use_remesh: Apply voxel remesh for organic look
    """
    
    print(f"\n{'='*60}")
    print(f"[Akku SDK v3.3] Character Generation")
    print(f"{'='*60}")
    print(f"Prompt: {prompt}")
    print(f"Style: {style}, Poly Level: {poly_level}")
    print(f"Gender: {gender}, Body Type: {body_type}")
    print(f"Use Remesh: {use_remesh}")
    print(f"{'='*60}\n")
    
    # Step 1: Load base mesh
    load_result = ToolRegistry.execute("load_base_mesh", {"gender": gender})
    if load_result["status"] == "error":
        raise RuntimeError(f"Load failed: {load_result['message']}")
    
    # Step 2: Apply body type deformation (BEFORE style/decimation)
    body_type_result = None
    if body_type != "default":
        # Auto-detect from prompt if set to "auto"
        if body_type == "auto":
            detected_params = BodyTypePresets.detect_from_prompt(prompt)
            # Only apply if non-default params detected
            if detected_params != BodyTypePresets.PRESETS["default"]:
                body_type_result = ToolRegistry.execute("apply_body_type", {
                    "body_type": "default",  # Use detected params directly
                    "muscular": detected_params.muscular,
                    "fat": detected_params.fat,
                    "height": detected_params.height,
                    "shoulder_width": detected_params.shoulder_width,
                    "hip_width": detected_params.hip_width
                })
        else:
            body_type_result = ToolRegistry.execute("apply_body_type", {
                "body_type": body_type
            })
    
    # Step 3: Apply style (color, material, decimation)
    style_result = ToolRegistry.execute("apply_style", {
        "prompt": prompt,
        "style": style,
        "poly_level": poly_level
    })
    if style_result["status"] == "error":
        raise RuntimeError(f"Style failed: {style_result['message']}")
    
    # Step 4: Optional - Union and Smooth for organic look
    remesh_result = None
    if use_remesh:
        poly_settings = StyleAnalyzer.get_poly_settings(poly_level)
        remesh_result = ToolRegistry.execute("union_and_smooth", {
            "voxel_size": poly_settings.get("voxel_size", 0.02),
            "smooth_iterations": 2
        })
    
    # Step 5: Export
    if output_path is None:
        output_path = os.path.join(AkkuConfig.OUTPUT_DIR, "character.glb")
    
    export_result = ToolRegistry.execute("export_glb", {"output_path": output_path})
    if export_result["status"] == "error":
        raise RuntimeError(f"Export failed: {export_result['message']}")
    
    return {
        "prompt": prompt,
        "style": style,
        "poly_level": poly_level,
        "body_type": body_type,
        "output_path": output_path,
        "load_info": load_result["result"],
        "body_type_info": body_type_result["result"] if body_type_result else None,
        "style_info": style_result["result"],
        "remesh_info": remesh_result["result"] if remesh_result else None,
        "export_info": export_result["result"]
    }


# ========================================
# CLI INTERFACE
# ========================================

def main():
    """Main entry point for CLI execution"""
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    
    if len(args) < 4:
        print("Usage: blender --background --python akku-sdk.py -- <prompt> <style> <poly_level> <output_path> [gender] [body_type] [use_remesh]")
        print("\nBody Types: default, muscular, thin, fat, tall, short, athletic, stocky, slim, heroic, chibi, giant")
        print("Korean: 근육질, 마른, 뚱뚱한, 키큰, 키작은, 운동선수, 땅딸막한, 날씬한, 영웅, 치비, 거인")
        sys.exit(1)
    
    prompt = args[0]
    style = args[1]
    poly_level = args[2]
    output_path = args[3]
    gender = args[4] if len(args) > 4 else "male"
    body_type = args[5] if len(args) > 5 else "auto"
    use_remesh = args[6].lower() == "true" if len(args) > 6 else False
    
    try:
        result = ToolRegistry.execute("generate_character", {
            "prompt": prompt,
            "style": style,
            "poly_level": poly_level,
            "output_path": output_path,
            "gender": gender,
            "body_type": body_type,
            "use_remesh": use_remesh
        })
        
        if result["status"] == "success":
            print(f"\n[Akku SDK] Generation completed successfully!")
            print(json.dumps(result["result"], indent=2, ensure_ascii=False, default=str))
        else:
            print(f"\n[Akku SDK] Generation failed: {result['message']}")
            if "error_report" in result:
                print(json.dumps(result["error_report"], indent=2, ensure_ascii=False))
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[Akku SDK] Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
