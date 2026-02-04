"""
Akku SDK Rigging - Auto Weight Transfer System

Transfers vertex weights from base mesh to attached parts using
Data Transfer modifier, enabling parts to follow bone animations
without manual weight painting.
"""

import bpy
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

from .core import AkkuLogger


@dataclass
class WeightTransferResult:
    """Result of weight transfer operation"""
    success: bool
    part_name: str
    source_mesh: str
    vertex_groups_created: int
    message: str


class AutoWeightTransfer:
    """
    Auto Weight Transfer System
    
    Uses Blender's Data Transfer modifier to copy vertex weights from
    the base character mesh to attached equipment parts. This allows
    parts to deform naturally with the armature without manual rigging.
    """
    
    @staticmethod
    def find_base_mesh() -> Optional[bpy.types.Object]:
        """Find the base character mesh (skinned mesh with armature modifier)"""
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE':
                    if obj.vertex_groups:
                        return obj
        return None
    
    @staticmethod
    def find_armature() -> Optional[bpy.types.Object]:
        """Find the character armature"""
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                return obj
        return None
    
    @staticmethod
    def get_mesh_vertex_groups(mesh: bpy.types.Object) -> List[str]:
        """Get list of vertex group names from a mesh"""
        if mesh and mesh.type == 'MESH':
            return [vg.name for vg in mesh.vertex_groups]
        return []
    
    @staticmethod
    def transfer_weights(
        source_mesh: bpy.types.Object,
        target_mesh: bpy.types.Object,
        max_distance: float = 0.5,
        apply_modifier: bool = True
    ) -> WeightTransferResult:
        """
        Transfer vertex weights from source mesh to target mesh
        
        Args:
            source_mesh: Base character mesh with vertex groups
            target_mesh: Equipment part to receive weights
            max_distance: Maximum distance for weight sampling (in Blender units)
            apply_modifier: Whether to apply the modifier after transfer
            
        Returns:
            WeightTransferResult with transfer status
        """
        if not source_mesh or source_mesh.type != 'MESH':
            return WeightTransferResult(
                success=False,
                part_name=target_mesh.name if target_mesh else "Unknown",
                source_mesh="None",
                vertex_groups_created=0,
                message="Invalid source mesh"
            )
        
        if not target_mesh or target_mesh.type != 'MESH':
            return WeightTransferResult(
                success=False,
                part_name="Unknown",
                source_mesh=source_mesh.name,
                vertex_groups_created=0,
                message="Invalid target mesh"
            )
        
        source_groups = AutoWeightTransfer.get_mesh_vertex_groups(source_mesh)
        if not source_groups:
            return WeightTransferResult(
                success=False,
                part_name=target_mesh.name,
                source_mesh=source_mesh.name,
                vertex_groups_created=0,
                message="Source mesh has no vertex groups"
            )
        
        for vg_name in source_groups:
            if vg_name not in target_mesh.vertex_groups:
                target_mesh.vertex_groups.new(name=vg_name)
        
        existing_dt = None
        for mod in target_mesh.modifiers:
            if mod.type == 'DATA_TRANSFER' and mod.name == "AkkuWeightTransfer":
                existing_dt = mod
                break
        
        if existing_dt:
            dt_mod = existing_dt
        else:
            dt_mod = target_mesh.modifiers.new(name="AkkuWeightTransfer", type='DATA_TRANSFER')
        
        dt_mod.object = source_mesh
        dt_mod.use_vert_data = True
        dt_mod.data_types_verts = {'VGROUP_WEIGHTS'}
        dt_mod.vert_mapping = 'POLYINTERP_NEAREST'
        dt_mod.mix_mode = 'REPLACE'
        dt_mod.mix_factor = 1.0
        
        dt_mod.use_max_distance = True
        dt_mod.max_distance = max_distance
        
        if apply_modifier:
            try:
                current_mode = bpy.context.mode
                if current_mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')
                
                bpy.ops.object.select_all(action='DESELECT')
                target_mesh.select_set(True)
                bpy.context.view_layer.objects.active = target_mesh
                
                bpy.ops.object.modifier_apply(modifier=dt_mod.name)
                
                AkkuLogger.info(f"Applied weight transfer to {target_mesh.name}")
            except Exception as e:
                AkkuLogger.warning(f"Could not apply modifier: {e}")
                return WeightTransferResult(
                    success=False,
                    part_name=target_mesh.name,
                    source_mesh=source_mesh.name,
                    vertex_groups_created=0,
                    message=f"Modifier apply failed: {e}"
                )
        
        groups_created = len(target_mesh.vertex_groups)
        
        return WeightTransferResult(
            success=True,
            part_name=target_mesh.name,
            source_mesh=source_mesh.name,
            vertex_groups_created=groups_created,
            message=f"Transferred {groups_created} vertex groups"
        )
    
    @staticmethod
    def add_armature_modifier(
        mesh: bpy.types.Object,
        armature: bpy.types.Object
    ) -> bool:
        """
        Add armature modifier to mesh if not already present
        
        Args:
            mesh: Target mesh object
            armature: Armature object
            
        Returns:
            True if modifier was added/exists, False on error
        """
        if not mesh or mesh.type != 'MESH':
            return False
        if not armature or armature.type != 'ARMATURE':
            return False
        
        for mod in mesh.modifiers:
            if mod.type == 'ARMATURE':
                mod.object = armature
                return True
        
        arm_mod = mesh.modifiers.new(name="Armature", type='ARMATURE')
        arm_mod.object = armature
        arm_mod.use_vertex_groups = True
        arm_mod.use_bone_envelopes = False
        
        AkkuLogger.info(f"Added armature modifier to {mesh.name}")
        return True
    
    @staticmethod
    def auto_rig_part(
        part: bpy.types.Object,
        apply_transfer: bool = True
    ) -> WeightTransferResult:
        """
        Automatically rig a part by transferring weights from base mesh
        
        This is the main entry point for auto weight transfer.
        It finds the base mesh and armature, transfers weights,
        and adds the armature modifier.
        
        Args:
            part: Equipment part mesh to rig
            apply_transfer: Whether to apply the data transfer modifier
            
        Returns:
            WeightTransferResult with operation status
        """
        base_mesh = AutoWeightTransfer.find_base_mesh()
        if not base_mesh:
            return WeightTransferResult(
                success=False,
                part_name=part.name if part else "Unknown",
                source_mesh="None",
                vertex_groups_created=0,
                message="No base mesh with weights found"
            )
        
        armature = AutoWeightTransfer.find_armature()
        if not armature:
            return WeightTransferResult(
                success=False,
                part_name=part.name if part else "Unknown",
                source_mesh=base_mesh.name,
                vertex_groups_created=0,
                message="No armature found"
            )
        
        result = AutoWeightTransfer.transfer_weights(
            source_mesh=base_mesh,
            target_mesh=part,
            max_distance=0.5,
            apply_modifier=apply_transfer
        )
        
        if result.success:
            AutoWeightTransfer.add_armature_modifier(part, armature)
            AkkuLogger.info(f"Auto-rigged part: {part.name}", {
                "source": base_mesh.name,
                "groups": result.vertex_groups_created
            })
        
        return result
    
    @staticmethod
    def auto_rig_all_parts(
        exclude_base: bool = True,
        apply_transfer: bool = True
    ) -> List[WeightTransferResult]:
        """
        Auto-rig all unrigged mesh parts in the scene
        
        Args:
            exclude_base: Whether to exclude the base mesh
            apply_transfer: Whether to apply the data transfer modifiers
            
        Returns:
            List of WeightTransferResult for each processed part
        """
        results = []
        base_mesh = AutoWeightTransfer.find_base_mesh()
        armature = AutoWeightTransfer.find_armature()
        
        if not base_mesh or not armature:
            AkkuLogger.warning("Cannot auto-rig: missing base mesh or armature")
            return results
        
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            
            if exclude_base and obj == base_mesh:
                continue
            
            has_armature_mod = any(m.type == 'ARMATURE' for m in obj.modifiers)
            if has_armature_mod and obj.vertex_groups:
                continue
            
            result = AutoWeightTransfer.auto_rig_part(obj, apply_transfer)
            results.append(result)
        
        AkkuLogger.info(f"Auto-rigged {len(results)} parts")
        return results
    
    @staticmethod
    def cleanup_zero_weights(
        mesh: bpy.types.Object,
        threshold: float = 0.001
    ) -> int:
        """
        Remove vertex groups with no significant weights
        
        Args:
            mesh: Mesh object to clean up
            threshold: Minimum weight to keep a vertex group
            
        Returns:
            Number of vertex groups removed
        """
        if not mesh or mesh.type != 'MESH':
            return 0
        
        groups_to_remove = []
        
        for vg in mesh.vertex_groups:
            has_weights = False
            for vert in mesh.data.vertices:
                try:
                    weight = vg.weight(vert.index)
                    if weight > threshold:
                        has_weights = True
                        break
                except RuntimeError:
                    continue
            
            if not has_weights:
                groups_to_remove.append(vg.name)
        
        for vg_name in groups_to_remove:
            vg = mesh.vertex_groups.get(vg_name)
            if vg:
                mesh.vertex_groups.remove(vg)
        
        if groups_to_remove:
            AkkuLogger.info(f"Removed {len(groups_to_remove)} empty vertex groups from {mesh.name}")
        
        return len(groups_to_remove)
