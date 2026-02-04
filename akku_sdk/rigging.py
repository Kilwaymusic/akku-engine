"""
Akku SDK Rigging - Auto Weight Transfer System
Uses Data Transfer modifier for context-independent weight copying
"""

import bpy
from typing import Optional, List
from dataclasses import dataclass

from .core import AkkuLogger


@dataclass
class WeightTransferResult:
    success: bool
    message: str
    vertex_groups_created: int = 0
    vertex_groups_cleaned: int = 0


class AutoWeightTransfer:
    @staticmethod
    def find_base_body() -> Optional[bpy.types.Object]:
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if any(name in obj.name.lower() for name in ['body', 'base', 'character', 'mesh']):
                    if obj.vertex_groups:
                        return obj
        for obj in bpy.data.objects:
            if obj.type == 'MESH' and obj.vertex_groups:
                return obj
        return None
    
    @staticmethod
    def find_armature() -> Optional[bpy.types.Object]:
        for obj in bpy.data.objects:
            if obj.type == 'ARMATURE':
                return obj
        return None
    
    @staticmethod
    def setup_armature_modifier(target_obj: bpy.types.Object, armature: bpy.types.Object) -> bool:
        for mod in target_obj.modifiers:
            if mod.type == 'ARMATURE':
                return True
        mod = target_obj.modifiers.new(name="Armature", type='ARMATURE')
        mod.object = armature
        mod.use_deform_preserve_volume = True
        return True
    
    @staticmethod
    def transfer_weights_via_modifier(source_obj: bpy.types.Object, target_obj: bpy.types.Object, apply_modifier: bool = True) -> WeightTransferResult:
        if not source_obj or not target_obj:
            return WeightTransferResult(False, "Invalid source or target object")
        if source_obj.type != 'MESH' or target_obj.type != 'MESH':
            return WeightTransferResult(False, "Both objects must be meshes")
        if not source_obj.vertex_groups:
            return WeightTransferResult(False, "Source has no vertex groups")
        initial_groups = len(target_obj.vertex_groups)
        for vg in source_obj.vertex_groups:
            if vg.name not in target_obj.vertex_groups:
                target_obj.vertex_groups.new(name=vg.name)
        mod = target_obj.modifiers.new(name="WeightTransfer", type='DATA_TRANSFER')
        mod.object = source_obj
        mod.use_vert_data = True
        mod.data_types_verts = {'VGROUP_WEIGHTS'}
        mod.vert_mapping = 'POLYINTERP_NEAREST'
        if apply_modifier:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            target_eval = target_obj.evaluated_get(depsgraph)
            target_obj.modifiers.remove(mod)
        final_groups = len(target_obj.vertex_groups)
        return WeightTransferResult(True, "Weight transfer completed", final_groups - initial_groups)
    
    @staticmethod
    def cleanup_zero_weights(obj: bpy.types.Object, threshold: float = 0.001) -> int:
        if not obj or obj.type != 'MESH':
            return 0
        empty_groups = []
        mesh = obj.data
        for vg in obj.vertex_groups:
            has_weights = False
            for v in mesh.vertices:
                try:
                    weight = vg.weight(v.index)
                    if weight > threshold:
                        has_weights = True
                        break
                except RuntimeError:
                    continue
            if not has_weights:
                empty_groups.append(vg.name)
        for name in empty_groups:
            vg = obj.vertex_groups.get(name)
            if vg:
                obj.vertex_groups.remove(vg)
        if empty_groups:
            AkkuLogger.info(f"Cleaned up {len(empty_groups)} empty vertex groups")
        return len(empty_groups)
    
    @staticmethod
    def auto_rig_part(part_obj: bpy.types.Object, source_body: bpy.types.Object = None, apply_transfer: bool = True) -> WeightTransferResult:
        if not part_obj:
            return WeightTransferResult(False, "No part object provided")
        if not source_body:
            source_body = AutoWeightTransfer.find_base_body()
        if not source_body:
            return WeightTransferResult(False, "No source body found for weight transfer")
        armature = AutoWeightTransfer.find_armature()
        if not armature:
            return WeightTransferResult(False, "No armature found in scene")
        result = AutoWeightTransfer.transfer_weights_via_modifier(source_body, part_obj, apply_transfer)
        if result.success:
            AutoWeightTransfer.setup_armature_modifier(part_obj, armature)
            cleaned = AutoWeightTransfer.cleanup_zero_weights(part_obj)
            result.vertex_groups_cleaned = cleaned
        return result
