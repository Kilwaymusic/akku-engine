"""
Akku SDK Core - Configuration, Logging, Error Handling
"""

import json
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class AkkuConfig:
    BASE_MESHES = {
        "male": "/home/composerkil/akku-engine/assets/base_meshes/Y_Bot.fbx",
        "female": "/home/composerkil/akku-engine/assets/base_meshes/X_Bot.fbx"
    }
    OUTPUT_DIR = "/home/composerkil/akku-engine/outputs"
    LOG_DIR = "/home/composerkil/akku-engine/logs"
    
    FBX_UNIT_SCALE = 0.01
    TARGET_HEIGHT = 1.8
    MIXAMO_FBX_PATH = "/home/composerkil/akku-engine/assets/base_meshes/Y_Bot.fbx"
    
    VOXEL_SIZE_DEFAULT = 0.02
    SMOOTH_ITERATIONS = 2
    SMOOTH_FACTOR = 0.5


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
