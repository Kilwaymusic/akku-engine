"""
Akku SDK Finalize - Game Engine Optimization Pipeline

Optimizes generated models for immediate use in Unity/Unreal:
- Duplicate vertex removal (merge by distance)
- Mesh joining (combine all parts)
- Material slot minimization
- Auto polygon reduction (Decimate) for mobile/PC targets
"""

import bpy
import bmesh
from typing import Dict, List, Optional, Tuple, Literal
from dataclasses import dataclass
from mathutils import Vector

from .core import AkkuLogger, MeshStats


@dataclass
class OptimizationResult:
    """Result of optimization operation"""
    success: bool
    original_verts: int
    final_verts: int
    original_tris: int
    final_tris: int
    original_materials: int
    final_materials: int
    reduction_percent: float
    errors: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "original_verts": self.original_verts,
            "final_verts": self.final_verts,
            "original_tris": self.original_tris,
            "final_tris": self.final_tris,
            "original_materials": self.original_materials,
            "final_materials": self.final_materials,
            "reduction_percent": round(self.reduction_percent, 2),
            "errors": self.errors
        }


@dataclass
class TargetProfile:
    """Platform target profile for optimization"""
    name: str
    max_triangles: int
    max_materials: int
    merge_distance: float
    decimate_ratio: float
    description: str


class PlatformTargets:
    """Pre-defined optimization profiles for different platforms"""
    
    MOBILE_LOW = TargetProfile(
        name="mobile_low",
        max_triangles=300,
        max_materials=1,
        merge_distance=0.01,
        decimate_ratio=0.15,
        description="Ultra-low mobile (300 tris)"
    )
    
    MOBILE = TargetProfile(
        name="mobile",
        max_triangles=800,
        max_materials=2,
        merge_distance=0.005,
        decimate_ratio=0.4,
        description="Standard mobile (800 tris)"
    )
    
    MOBILE_HIGH = TargetProfile(
        name="mobile_high",
        max_triangles=1500,
        max_materials=3,
        merge_distance=0.003,
        decimate_ratio=0.6,
        description="High-end mobile (1500 tris)"
    )
    
    PC_LOW = TargetProfile(
        name="pc_low",
        max_triangles=3000,
        max_materials=4,
        merge_distance=0.002,
        decimate_ratio=0.8,
        description="Low-spec PC (3000 tris)"
    )
    
    PC = TargetProfile(
        name="pc",
        max_triangles=5000,
        max_materials=6,
        merge_distance=0.001,
        decimate_ratio=0.9,
        description="Standard PC (5000 tris)"
    )
    
    PC_HIGH = TargetProfile(
        name="pc_high",
        max_triangles=10000,
        max_materials=8,
        merge_distance=0.0005,
        decimate_ratio=1.0,
        description="High-end PC (10000 tris)"
    )
    
    @classmethod
    def get_profile(cls, name: str) -> TargetProfile:
        """Get profile by name"""
        profiles = {
            "mobile_low": cls.MOBILE_LOW,
            "mobile": cls.MOBILE,
            "mobile_high": cls.MOBILE_HIGH,
            "pc_low": cls.PC_LOW,
            "pc": cls.PC,
            "pc_high": cls.PC_HIGH,
        }
        return profiles.get(name, cls.MOBILE)
    
    @classmethod
    def list_profiles(cls) -> List[Dict]:
        """List all available profiles"""
        return [
            {"name": "mobile_low", "tris": 300, "desc": "Ultra-low mobile"},
            {"name": "mobile", "tris": 800, "desc": "Standard mobile"},
            {"name": "mobile_high", "tris": 1500, "desc": "High-end mobile"},
            {"name": "pc_low", "tris": 3000, "desc": "Low-spec PC"},
            {"name": "pc", "tris": 5000, "desc": "Standard PC"},
            {"name": "pc_high", "tris": 10000, "desc": "High-end PC"},
        ]


class MeshOptimizer:
    """Low-level mesh optimization operations using bmesh (context-independent)"""
    
    @staticmethod
    def remove_doubles(obj: bpy.types.Object, distance: float = 0.001) -> int:
        """Remove duplicate vertices within distance threshold
        
        Args:
            obj: Target mesh object
            distance: Merge distance threshold
            
        Returns:
            Number of vertices removed
        """
        if obj.type != 'MESH':
            return 0
            
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        original_count = len(bm.verts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=distance)
        removed = original_count - len(bm.verts)
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        if removed > 0:
            AkkuLogger.debug(f"Removed {removed} duplicate vertices from '{obj.name}'", 
                           {"distance": distance})
        
        return removed
    
    @staticmethod
    def dissolve_degenerate(obj: bpy.types.Object, threshold: float = 0.0001) -> int:
        """Remove degenerate geometry (zero-area faces, zero-length edges)
        
        Args:
            obj: Target mesh object
            threshold: Size threshold for degenerate detection
            
        Returns:
            Number of elements removed
        """
        if obj.type != 'MESH':
            return 0
            
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        original_faces = len(bm.faces)
        original_edges = len(bm.edges)
        
        bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=threshold)
        
        removed = (original_faces - len(bm.faces)) + (original_edges - len(bm.edges))
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return removed
    
    @staticmethod
    def recalculate_normals(obj: bpy.types.Object, inside: bool = False) -> bool:
        """Recalculate face normals to ensure consistent orientation
        
        Args:
            obj: Target mesh object
            inside: If True, flip normals inward
            
        Returns:
            Success status
        """
        if obj.type != 'MESH':
            return False
            
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        
        if inside:
            for face in bm.faces:
                face.normal_flip()
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        AkkuLogger.debug(f"Recalculated normals for '{obj.name}'")
        return True
    
    @staticmethod
    def get_triangle_count(obj: bpy.types.Object) -> int:
        """Get total triangle count for a mesh object"""
        if obj.type != 'MESH':
            return 0
            
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        tri_count = len(bm.faces)
        bm.free()
        
        return tri_count
    
    @staticmethod
    def limited_dissolve(obj: bpy.types.Object, angle_limit: float = 5.0) -> int:
        """Dissolve edges/verts based on angle threshold to reduce poly count
        
        Args:
            obj: Target mesh object
            angle_limit: Maximum angle (degrees) for dissolve
            
        Returns:
            Number of faces reduced
        """
        if obj.type != 'MESH':
            return 0
            
        import math
        angle_rad = math.radians(angle_limit)
        
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        original_faces = len(bm.faces)
        bmesh.ops.dissolve_limit(bm, 
                                  angle_limit=angle_rad,
                                  verts=bm.verts,
                                  edges=bm.edges)
        reduced = original_faces - len(bm.faces)
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        
        return reduced


class MaterialOptimizer:
    """Material slot optimization operations (context-independent)"""
    
    @staticmethod
    def remove_unused_slots(obj: bpy.types.Object) -> int:
        """Remove material slots that aren't used by any faces (context-independent)
        
        Uses direct data-block manipulation instead of bpy.ops.
        
        Args:
            obj: Target mesh object
            
        Returns:
            Number of slots removed
        """
        if obj.type != 'MESH':
            return 0
        
        mesh = obj.data
        used_indices = set()
        for poly in mesh.polygons:
            used_indices.add(poly.material_index)
        
        materials_to_keep = []
        index_remap = {}
        new_index = 0
        
        for i in range(len(mesh.materials)):
            if i in used_indices:
                materials_to_keep.append(mesh.materials[i])
                index_remap[i] = new_index
                new_index += 1
        
        removed_count = len(mesh.materials) - len(materials_to_keep)
        
        if removed_count == 0:
            return 0
        
        for poly in mesh.polygons:
            if poly.material_index in index_remap:
                poly.material_index = index_remap[poly.material_index]
            else:
                poly.material_index = 0
        
        mesh.materials.clear()
        for mat in materials_to_keep:
            mesh.materials.append(mat)
        
        if removed_count > 0:
            AkkuLogger.debug(f"Removed {removed_count} unused material slots from '{obj.name}'")
        
        return removed_count
    
    @staticmethod
    def merge_identical_materials(obj: bpy.types.Object) -> int:
        """Merge material slots with identical materials (context-independent)
        
        Args:
            obj: Target mesh object
            
        Returns:
            Number of slots merged
        """
        if obj.type != 'MESH':
            return 0
        
        mesh = obj.data
        if len(mesh.materials) < 2:
            return 0
        
        material_map = {}
        merge_map = {}
        
        for i, mat in enumerate(mesh.materials):
            if mat:
                base_name = mat.name.split('.')[0]
                
                if base_name not in material_map:
                    material_map[base_name] = i
                else:
                    merge_map[i] = material_map[base_name]
        
        if not merge_map:
            return 0
        
        for poly in mesh.polygons:
            if poly.material_index in merge_map:
                poly.material_index = merge_map[poly.material_index]
        
        MaterialOptimizer.remove_unused_slots(obj)
        
        merged = len(merge_map)
        AkkuLogger.debug(f"Merged {merged} duplicate material slots in '{obj.name}'")
        
        return merged
    
    @staticmethod
    def consolidate_to_single_material(obj: bpy.types.Object, 
                                        base_color: Tuple[float, float, float] = (0.5, 0.5, 0.5)) -> bool:
        """Consolidate all materials into a single atlas-ready material (context-independent)
        
        Uses direct mesh.materials manipulation instead of bpy.ops.
        
        Args:
            obj: Target mesh object
            base_color: RGB base color for consolidated material
            
        Returns:
            Success status
        """
        if obj.type != 'MESH':
            return False
        
        mesh = obj.data
        
        for poly in mesh.polygons:
            poly.material_index = 0
        
        first_mat = mesh.materials[0] if len(mesh.materials) > 0 else None
        
        mesh.materials.clear()
        
        if first_mat:
            mesh.materials.append(first_mat)
            mat = first_mat
        else:
            mat = bpy.data.materials.new(name="Consolidated_Material")
            mesh.materials.append(mat)
        
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
        
        AkkuLogger.info(f"Consolidated materials in '{obj.name}' to single material")
        return True
    
    @staticmethod
    def reduce_to_limit(obj: bpy.types.Object, max_materials: int) -> int:
        """Reduce material slots to a maximum limit (context-independent)
        
        Merges less-used material slots into more-used ones until limit is reached.
        Handles empty slots and unused indices safely.
        
        Args:
            obj: Target mesh object
            max_materials: Maximum allowed material slots
            
        Returns:
            Number of materials reduced
        """
        if obj.type != 'MESH':
            return 0
        
        mesh = obj.data
        current_count = len(mesh.materials)
        
        if current_count <= max_materials:
            return 0
        
        if max_materials <= 0:
            max_materials = 1
        
        if max_materials == 1:
            MaterialOptimizer.consolidate_to_single_material(obj)
            return current_count - 1
        
        usage_count = {}
        for i in range(len(mesh.materials)):
            usage_count[i] = 0
        for poly in mesh.polygons:
            idx = poly.material_index
            if idx < len(mesh.materials):
                usage_count[idx] = usage_count.get(idx, 0) + 1
        
        sorted_indices = sorted(usage_count.keys(), key=lambda x: usage_count.get(x, 0), reverse=True)
        
        keep_count = min(max_materials, len(sorted_indices))
        keep_indices = set(sorted_indices[:keep_count])
        
        primary_idx = sorted_indices[0] if sorted_indices else 0
        remap = {}
        
        for idx in range(len(mesh.materials)):
            if idx not in keep_indices:
                remap[idx] = primary_idx
        
        for poly in mesh.polygons:
            if poly.material_index in remap:
                poly.material_index = remap[poly.material_index]
            elif poly.material_index >= len(mesh.materials):
                poly.material_index = primary_idx
        
        materials_to_keep = []
        new_index_map = {}
        new_idx = 0
        
        for i in sorted_indices[:keep_count]:
            if i < len(mesh.materials):
                materials_to_keep.append(mesh.materials[i])
                new_index_map[i] = new_idx
                new_idx += 1
        
        for poly in mesh.polygons:
            old_idx = poly.material_index
            if old_idx in new_index_map:
                poly.material_index = new_index_map[old_idx]
            else:
                poly.material_index = 0
        
        mesh.materials.clear()
        for mat in materials_to_keep:
            mesh.materials.append(mat)
        
        reduced = current_count - len(mesh.materials)
        AkkuLogger.info(f"Reduced materials in '{obj.name}': {current_count} → {len(mesh.materials)}")
        
        return reduced


class DecimateEngine:
    """Polygon reduction using Decimate modifier or bmesh fallback"""
    
    @staticmethod
    def _get_depsgraph_safe():
        """Get depsgraph in a context-safe manner"""
        try:
            if hasattr(bpy.context, 'evaluated_depsgraph_get'):
                return bpy.context.evaluated_depsgraph_get()
        except:
            pass
        
        try:
            if bpy.context.view_layer:
                return bpy.context.view_layer.depsgraph
        except:
            pass
        
        return None
    
    @staticmethod
    def _bmesh_decimate(obj: bpy.types.Object, ratio: float) -> bool:
        """Fallback bmesh-based decimation when no context available"""
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        
        target_faces = max(4, int(len(bm.faces) * ratio))
        
        while len(bm.faces) > target_faces:
            shortest_edge = min(bm.edges, key=lambda e: e.calc_length())
            try:
                bmesh.ops.collapse(bm, edges=[shortest_edge])
            except:
                break
        
        bm.to_mesh(obj.data)
        bm.free()
        obj.data.update()
        return True
    
    @staticmethod
    def decimate_to_target(obj: bpy.types.Object, 
                           target_tris: int,
                           method: Literal["collapse", "planar", "unsubdiv"] = "collapse") -> Tuple[int, int]:
        """Reduce polygon count to target triangle count
        
        Uses modifier-based decimation with depsgraph, falls back to bmesh if no context.
        
        Args:
            obj: Target mesh object
            target_tris: Target triangle count
            method: Decimation method
            
        Returns:
            Tuple of (original_tris, final_tris)
        """
        if obj.type != 'MESH':
            return (0, 0)
            
        original_tris = MeshOptimizer.get_triangle_count(obj)
        
        if original_tris <= target_tris:
            return (original_tris, original_tris)
        
        ratio = target_tris / original_tris
        ratio = max(0.01, min(1.0, ratio))
        
        depsgraph = DecimateEngine._get_depsgraph_safe()
        
        if depsgraph is None:
            AkkuLogger.debug(f"No context available, using bmesh decimation for '{obj.name}'")
            DecimateEngine._bmesh_decimate(obj, ratio)
            final_tris = MeshOptimizer.get_triangle_count(obj)
            return (original_tris, final_tris)
        
        mod = obj.modifiers.new(name="AkkuDecimate", type='DECIMATE')
        mod.decimate_type = method.upper() if method in ["collapse", "unsubdiv"] else "DISSOLVE"
        
        if method == "collapse":
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
        elif method == "planar":
            mod.decimate_type = "DISSOLVE"
            mod.angle_limit = 0.087
        elif method == "unsubdiv":
            mod.iterations = max(1, int((1 - ratio) * 5))
        
        try:
            depsgraph.update()
            obj_eval = obj.evaluated_get(depsgraph)
            new_mesh = bpy.data.meshes.new_from_object(obj_eval)
            old_mesh = obj.data
            obj.data = new_mesh
            obj.modifiers.remove(mod)
            
            if old_mesh.users == 0:
                bpy.data.meshes.remove(old_mesh)
        except Exception as e:
            obj.modifiers.remove(mod)
            AkkuLogger.debug(f"Modifier decimation failed, using bmesh fallback: {e}")
            DecimateEngine._bmesh_decimate(obj, ratio)
        
        final_tris = MeshOptimizer.get_triangle_count(obj)
        
        AkkuLogger.info(f"Decimated '{obj.name}': {original_tris} → {final_tris} triangles", {
            "target": target_tris,
            "method": method,
            "ratio": round(ratio, 3)
        })
        
        return (original_tris, final_tris)
    
    @staticmethod
    def decimate_by_ratio(obj: bpy.types.Object, ratio: float = 0.5) -> Tuple[int, int]:
        """Reduce polygon count by ratio
        
        Args:
            obj: Target mesh object
            ratio: Ratio of polygons to keep (0.0 to 1.0)
            
        Returns:
            Tuple of (original_tris, final_tris)
        """
        if obj.type != 'MESH':
            return (0, 0)
            
        original_tris = MeshOptimizer.get_triangle_count(obj)
        target_tris = int(original_tris * ratio)
        
        return DecimateEngine.decimate_to_target(obj, target_tris)


class MeshJoiner:
    """Join multiple mesh objects into a single mesh (context-independent)
    
    Note: Optimized for low-poly character models. For complex meshes with
    extensive UV/vertex weight data, use bpy.ops.object.join with proper context.
    """
    
    @staticmethod
    def join_objects(objects: List[bpy.types.Object], 
                     new_name: str = "Joined_Character") -> Optional[bpy.types.Object]:
        """Join multiple mesh objects into one (context-independent)
        
        Uses bmesh for proper mesh data transfer including UVs and materials.
        Designed for low-poly procedural models.
        
        Args:
            objects: List of mesh objects to join
            new_name: Name for the joined object
            
        Returns:
            Joined mesh object or None
        """
        mesh_objects = [obj for obj in objects if obj.type == 'MESH']
        
        if len(mesh_objects) == 0:
            AkkuLogger.error("No mesh objects to join")
            return None
        
        if len(mesh_objects) == 1:
            mesh_objects[0].name = new_name
            return mesh_objects[0]
        
        combined_bm = bmesh.new()
        material_list = []
        
        uv_layer = None
        
        for obj in mesh_objects:
            mesh = obj.data
            
            temp_bm = bmesh.new()
            temp_bm.from_mesh(mesh)
            
            temp_bm.transform(obj.matrix_world)
            
            mat_remap = {}
            for i, mat in enumerate(mesh.materials):
                if mat not in material_list:
                    material_list.append(mat)
                mat_remap[i] = material_list.index(mat)
            
            vert_map = {}
            for v in temp_bm.verts:
                new_v = combined_bm.verts.new(v.co)
                vert_map[v.index] = new_v
            
            combined_bm.verts.ensure_lookup_table()
            combined_bm.verts.index_update()
            
            if uv_layer is None and len(temp_bm.loops.layers.uv) > 0:
                uv_layer = combined_bm.loops.layers.uv.new("UVMap")
            
            temp_uv_layer = temp_bm.loops.layers.uv.active if temp_bm.loops.layers.uv else None
            
            for f in temp_bm.faces:
                try:
                    new_verts = [vert_map[v.index] for v in f.verts]
                    new_face = combined_bm.faces.new(new_verts)
                    new_face.material_index = mat_remap.get(f.material_index, 0)
                    
                    if temp_uv_layer and uv_layer:
                        for i, loop in enumerate(new_face.loops):
                            old_uv = f.loops[i][temp_uv_layer].uv
                            loop[uv_layer].uv = old_uv.copy()
                except:
                    pass
            
            temp_bm.free()
        
        new_mesh = bpy.data.meshes.new(name=f"{new_name}_mesh")
        combined_bm.to_mesh(new_mesh)
        combined_bm.free()
        
        for mat in material_list:
            new_mesh.materials.append(mat)
        
        target_obj = mesh_objects[0]
        old_mesh = target_obj.data
        target_obj.data = new_mesh
        target_obj.name = new_name
        
        from mathutils import Matrix
        target_obj.matrix_world = Matrix.Identity(4)
        
        for obj in mesh_objects[1:]:
            if obj.name in bpy.data.objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        
        AkkuLogger.info(f"Joined {len(mesh_objects)} objects into '{new_name}'", {
            "materials": len(material_list),
            "has_uv": uv_layer is not None
        })
        
        return target_obj
    
    @staticmethod
    def join_by_material(objects: List[bpy.types.Object]) -> List[bpy.types.Object]:
        """Join objects that share the same material
        
        Args:
            objects: List of mesh objects
            
        Returns:
            List of joined objects (one per unique material)
        """
        material_groups: Dict[str, List[bpy.types.Object]] = {}
        
        for obj in objects:
            if obj.type != 'MESH':
                continue
            
            mesh = obj.data
            if len(mesh.materials) > 0 and mesh.materials[0]:
                mat_name = mesh.materials[0].name
            else:
                mat_name = "__no_material__"
            
            if mat_name not in material_groups:
                material_groups[mat_name] = []
            material_groups[mat_name].append(obj)
        
        joined_objects = []
        for mat_name, group_objects in material_groups.items():
            joined = MeshJoiner.join_objects(group_objects, f"Joined_{mat_name}")
            if joined:
                joined_objects.append(joined)
        
        return joined_objects


class FinalizePipeline:
    """
    Complete game engine optimization pipeline
    
    Orchestrates all optimization steps for Unity/Unreal export:
    1. Remove duplicate vertices
    2. Join meshes
    3. Optimize materials
    4. Decimate to target platform
    5. Recalculate normals
    6. Final cleanup
    """
    
    def __init__(self, target: str = "mobile"):
        """Initialize pipeline with target platform
        
        Args:
            target: Platform profile name (mobile_low, mobile, mobile_high, pc_low, pc, pc_high)
        """
        self.profile = PlatformTargets.get_profile(target)
        self.errors: List[str] = []
    
    def optimize_object(self, obj: bpy.types.Object) -> OptimizationResult:
        """Run full optimization pipeline on a single object
        
        Args:
            obj: Target mesh object
            
        Returns:
            OptimizationResult with statistics
        """
        if obj.type != 'MESH':
            return OptimizationResult(
                success=False,
                original_verts=0, final_verts=0,
                original_tris=0, final_tris=0,
                original_materials=0, final_materials=0,
                reduction_percent=0,
                errors=["Object is not a mesh"]
            )
        
        original_verts = len(obj.data.vertices)
        original_tris = MeshOptimizer.get_triangle_count(obj)
        original_materials = len(obj.material_slots)
        
        AkkuLogger.info(f"Starting optimization pipeline for '{obj.name}'", {
            "profile": self.profile.name,
            "target_tris": self.profile.max_triangles
        })
        
        try:
            MeshOptimizer.remove_doubles(obj, self.profile.merge_distance)
            MeshOptimizer.dissolve_degenerate(obj)
            MaterialOptimizer.merge_identical_materials(obj)
            MaterialOptimizer.remove_unused_slots(obj)
            
            current_tris = MeshOptimizer.get_triangle_count(obj)
            if current_tris > self.profile.max_triangles:
                DecimateEngine.decimate_to_target(obj, self.profile.max_triangles)
            elif self.profile.decimate_ratio < 1.0:
                target_by_ratio = int(current_tris * self.profile.decimate_ratio)
                if target_by_ratio < current_tris:
                    DecimateEngine.decimate_to_target(obj, target_by_ratio)
            
            current_materials = len(obj.data.materials)
            if current_materials > self.profile.max_materials:
                MaterialOptimizer.reduce_to_limit(obj, self.profile.max_materials)
            
            MeshOptimizer.recalculate_normals(obj)
            
            final_verts = len(obj.data.vertices)
            final_tris = MeshOptimizer.get_triangle_count(obj)
            final_materials = len(obj.material_slots)
            
            reduction = ((original_tris - final_tris) / original_tris * 100) if original_tris > 0 else 0
            
            result = OptimizationResult(
                success=True,
                original_verts=original_verts,
                final_verts=final_verts,
                original_tris=original_tris,
                final_tris=final_tris,
                original_materials=original_materials,
                final_materials=final_materials,
                reduction_percent=reduction,
                errors=self.errors
            )
            
            AkkuLogger.info(f"Optimization complete for '{obj.name}'", result.to_dict())
            return result
            
        except Exception as e:
            error_msg = f"Optimization failed: {str(e)}"
            self.errors.append(error_msg)
            AkkuLogger.error(error_msg)
            
            return OptimizationResult(
                success=False,
                original_verts=original_verts,
                final_verts=len(obj.data.vertices),
                original_tris=original_tris,
                final_tris=MeshOptimizer.get_triangle_count(obj),
                original_materials=original_materials,
                final_materials=len(obj.material_slots),
                reduction_percent=0,
                errors=self.errors
            )
    
    def optimize_character(self, 
                           root_obj: Optional[bpy.types.Object] = None,
                           mesh_objects: Optional[List[bpy.types.Object]] = None,
                           join_meshes: bool = True) -> OptimizationResult:
        """Optimize entire character (multiple objects) - context-independent
        
        Args:
            root_obj: Root object (armature or parent). Optional.
            mesh_objects: List of mesh objects to optimize. Required if root_obj is None.
            join_meshes: Whether to join all meshes into one
            
        Returns:
            OptimizationResult for the final character
        """
        if mesh_objects:
            mesh_objects = [obj for obj in mesh_objects if obj.type == 'MESH']
        elif root_obj and root_obj.type == 'ARMATURE':
            mesh_objects = [child for child in root_obj.children if child.type == 'MESH']
        elif root_obj and root_obj.type == 'MESH':
            mesh_objects = [root_obj]
        else:
            mesh_objects = []
        
        if not mesh_objects:
            return OptimizationResult(
                success=False,
                original_verts=0, final_verts=0,
                original_tris=0, final_tris=0,
                original_materials=0, final_materials=0,
                reduction_percent=0,
                errors=["No mesh objects found"]
            )
        
        total_original_verts = sum(len(obj.data.vertices) for obj in mesh_objects)
        total_original_tris = sum(MeshOptimizer.get_triangle_count(obj) for obj in mesh_objects)
        total_original_materials = sum(len(obj.material_slots) for obj in mesh_objects)
        
        if join_meshes and len(mesh_objects) > 1:
            target_obj = MeshJoiner.join_objects(mesh_objects, "Optimized_Character")
            mesh_objects = [target_obj] if target_obj else []
        
        for obj in mesh_objects:
            self.optimize_object(obj)
        
        if mesh_objects:
            final_obj = mesh_objects[0]
            final_verts = len(final_obj.data.vertices)
            final_tris = MeshOptimizer.get_triangle_count(final_obj)
            final_materials = len(final_obj.material_slots)
        else:
            final_verts = 0
            final_tris = 0
            final_materials = 0
        
        reduction = ((total_original_tris - final_tris) / total_original_tris * 100) if total_original_tris > 0 else 0
        
        return OptimizationResult(
            success=True,
            original_verts=total_original_verts,
            final_verts=final_verts,
            original_tris=total_original_tris,
            final_tris=final_tris,
            original_materials=total_original_materials,
            final_materials=final_materials,
            reduction_percent=reduction,
            errors=self.errors
        )
    
    @staticmethod
    def quick_optimize(obj: bpy.types.Object, target: str = "mobile") -> OptimizationResult:
        """Convenience method for quick single-object optimization
        
        Args:
            obj: Target mesh object
            target: Platform profile name
            
        Returns:
            OptimizationResult
        """
        pipeline = FinalizePipeline(target)
        return pipeline.optimize_object(obj)
    
    @staticmethod
    def create_lod_chain(obj: bpy.types.Object, 
                         collection: Optional[bpy.types.Collection] = None) -> Dict[str, bpy.types.Object]:
        """Create LOD (Level of Detail) chain for the object
        
        Context-independent: collection can be passed explicitly.
        
        Args:
            obj: Source mesh object
            collection: Collection to link LOD objects to. If None, uses obj's collection.
            
        Returns:
            Dict mapping LOD names to objects
        """
        if obj.type != 'MESH':
            return {}
        
        if collection is None:
            for coll in bpy.data.collections:
                if obj.name in coll.objects:
                    collection = coll
                    break
            if collection is None:
                collection = bpy.data.collections.get("Collection")
                if collection is None:
                    collection = bpy.data.collections.new("LOD_Collection")
                    if hasattr(bpy.context, 'scene') and bpy.context.scene:
                        bpy.context.scene.collection.children.link(collection)
        
        lod_chain = {}
        lod_profiles = [
            ("LOD0", "pc_high"),
            ("LOD1", "pc"),
            ("LOD2", "mobile_high"),
            ("LOD3", "mobile"),
        ]
        
        for lod_name, profile_name in lod_profiles:
            lod_obj = obj.copy()
            lod_obj.data = obj.data.copy()
            lod_obj.name = f"{obj.name}_{lod_name}"
            
            if collection:
                collection.objects.link(lod_obj)
            
            pipeline = FinalizePipeline(profile_name)
            pipeline.optimize_object(lod_obj)
            
            lod_chain[lod_name] = lod_obj
        
        AkkuLogger.info(f"Created LOD chain for '{obj.name}'", {
            "lods": list(lod_chain.keys())
        })
        
        return lod_chain
