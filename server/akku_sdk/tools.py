"""
Akku SDK Tools - Tool Registry and Style Analyzer
"""

import bpy
import bmesh
import time
from datetime import datetime
from typing import Dict, Any, Callable, List, Tuple
from functools import wraps
from dataclasses import asdict

from .core import AkkuLogger, MeshStats, StepResult


class MeshAnalyzer:
    """Analyzes mesh and provides statistics"""
    
    @staticmethod
    def get_stats(obj) -> MeshStats:
        """Get comprehensive mesh statistics"""
        if obj.type != 'MESH':
            return MeshStats()
        
        mesh = obj.data
        
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tri_count = len(bm.faces)
        bm.free()
        
        from mathutils import Vector
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
    def log_stats(obj, label: str = ""):
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


class ToolRegistry:
    """MCP-style tool registry with integrated error handling"""
    
    _tools: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, description: str = ""):
        """Decorator to register a tool function with error handling"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                AkkuLogger.info(f"Executing tool: {name}")
                
                try:
                    result = func(*args, **kwargs)
                    duration = (time.time() - start_time) * 1000
                    
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
                    
                    mesh_stats = None
                    mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
                    if mesh_objects:
                        mesh_stats = MeshAnalyzer.get_stats(mesh_objects[0])
                    
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


tool = ToolRegistry.register


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
