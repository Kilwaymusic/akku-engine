"""
Akku SDK v4.0 - Atomic Modeling Operations

Low-level BMesh operations for procedural mesh manipulation.
Provides Face selection, Inset, Extrude, and Vertex Color operations.
"""

import bpy
import bmesh
import math
from mathutils import Vector, Color
from typing import List, Set, Dict, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum


class FaceSelectionMode(Enum):
    """Face selection criteria"""
    BY_NORMAL = "normal"
    BY_POSITION = "position"
    BY_MATERIAL = "material"
    BY_INDEX = "index"
    BY_AREA = "area"


@dataclass
class FaceSelector:
    """Configuration for face selection"""
    mode: FaceSelectionMode
    direction: Optional[Vector] = None
    threshold: float = 0.7
    position_min: Optional[Vector] = None
    position_max: Optional[Vector] = None
    material_index: int = 0
    indices: Optional[List[int]] = None
    min_area: float = 0.0
    max_area: float = float('inf')


class AtomicOps:
    """
    Atomic BMesh Operations Module
    
    Provides low-level mesh manipulation functions that can be
    composed to create complex hard-surface details.
    """
    
    @staticmethod
    def get_bmesh(obj: bpy.types.Object) -> bmesh.types.BMesh:
        """Get BMesh from object, creating if needed"""
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        return bm
    
    @staticmethod
    def apply_bmesh(bm: bmesh.types.BMesh, obj: bpy.types.Object, free: bool = True):
        """Apply BMesh changes to object"""
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(obj.data)
        if free:
            bm.free()
        obj.data.update()
    
    @classmethod
    def select_faces(
        cls,
        bm: bmesh.types.BMesh,
        selector: FaceSelector
    ) -> List[bmesh.types.BMFace]:
        """
        Select faces based on criteria.
        Returns list of selected faces.
        """
        selected = []
        
        for face in bm.faces:
            if cls._face_matches(face, selector):
                selected.append(face)
        
        return selected
    
    @classmethod
    def _face_matches(cls, face: bmesh.types.BMFace, selector: FaceSelector) -> bool:
        """Check if face matches selection criteria"""
        
        if selector.mode == FaceSelectionMode.BY_NORMAL:
            if selector.direction is None:
                return False
            dot = face.normal.dot(selector.direction.normalized())
            return dot >= selector.threshold
        
        elif selector.mode == FaceSelectionMode.BY_POSITION:
            center = face.calc_center_median()
            if selector.position_min and selector.position_max:
                return (
                    selector.position_min.x <= center.x <= selector.position_max.x and
                    selector.position_min.y <= center.y <= selector.position_max.y and
                    selector.position_min.z <= center.z <= selector.position_max.z
                )
            return False
        
        elif selector.mode == FaceSelectionMode.BY_MATERIAL:
            return face.material_index == selector.material_index
        
        elif selector.mode == FaceSelectionMode.BY_INDEX:
            if selector.indices is None:
                return False
            return face.index in selector.indices
        
        elif selector.mode == FaceSelectionMode.BY_AREA:
            area = face.calc_area()
            return selector.min_area <= area <= selector.max_area
        
        return False
    
    @classmethod
    def select_faces_by_normal(
        cls,
        bm: bmesh.types.BMesh,
        direction: Vector,
        threshold: float = 0.7
    ) -> List[bmesh.types.BMFace]:
        """Select faces pointing in a direction"""
        selector = FaceSelector(
            mode=FaceSelectionMode.BY_NORMAL,
            direction=direction,
            threshold=threshold
        )
        return cls.select_faces(bm, selector)
    
    @classmethod
    def select_faces_by_position(
        cls,
        bm: bmesh.types.BMesh,
        min_pos: Vector,
        max_pos: Vector
    ) -> List[bmesh.types.BMFace]:
        """Select faces within bounding box"""
        selector = FaceSelector(
            mode=FaceSelectionMode.BY_POSITION,
            position_min=min_pos,
            position_max=max_pos
        )
        return cls.select_faces(bm, selector)
    
    @classmethod
    def inset_faces(
        cls,
        bm: bmesh.types.BMesh,
        faces: List[bmesh.types.BMFace],
        thickness: float = 0.02,
        depth: float = 0.0,
        use_boundary: bool = True,
        use_even_offset: bool = True
    ) -> Dict:
        """
        Inset selected faces.
        Returns dict with new geometry references.
        """
        result = bmesh.ops.inset_region(
            bm,
            faces=faces,
            thickness=thickness,
            depth=depth,
            use_boundary=use_boundary,
            use_even_offset=use_even_offset
        )
        
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        return result
    
    @classmethod
    def extrude_faces(
        cls,
        bm: bmesh.types.BMesh,
        faces: List[bmesh.types.BMFace],
        offset: float = 0.05,
        direction: Optional[Vector] = None
    ) -> List[bmesh.types.BMFace]:
        """
        Extrude faces along their normals or specified direction.
        Returns list of new top faces.
        """
        result = bmesh.ops.extrude_face_region(bm, geom=faces)
        
        new_verts = [g for g in result['geom'] if isinstance(g, bmesh.types.BMVert)]
        new_faces = [g for g in result['geom'] if isinstance(g, bmesh.types.BMFace)]
        
        for vert in new_verts:
            if direction:
                vert.co += direction.normalized() * offset
            else:
                avg_normal = Vector((0, 0, 0))
                for face in vert.link_faces:
                    avg_normal += face.normal
                if avg_normal.length > 0:
                    avg_normal.normalize()
                    vert.co += avg_normal * offset
        
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        
        return new_faces
    
    @classmethod
    def inset_extrude(
        cls,
        bm: bmesh.types.BMesh,
        faces: List[bmesh.types.BMFace],
        inset_thickness: float = 0.02,
        extrude_depth: float = 0.05
    ) -> List[bmesh.types.BMFace]:
        """
        Inset then extrude faces - creates armor/panel effect.
        Returns the extruded top faces.
        """
        result = bmesh.ops.inset_region(
            bm,
            faces=faces,
            thickness=inset_thickness,
            depth=0.0,
            use_boundary=True,
            use_even_offset=True
        )
        
        bm.faces.ensure_lookup_table()
        
        inset_inner_faces = [f for f in faces if f.is_valid]
        
        if not inset_inner_faces:
            return []
        
        new_faces = cls.extrude_faces(bm, inset_inner_faces, offset=extrude_depth)
        
        return new_faces


class VertexColorOps:
    """
    Vertex Color Operations
    
    Provides functions to paint vertex colors on mesh geometry.
    GLB export preserves vertex colors reliably.
    """
    
    @staticmethod
    def ensure_color_layer(
        bm: bmesh.types.BMesh,
        name: str = "Col"
    ) -> bmesh.types.BMLayerItem:
        """Get or create vertex color layer"""
        color_layer = bm.loops.layers.color.get(name)
        if color_layer is None:
            color_layer = bm.loops.layers.color.new(name)
        return color_layer
    
    @classmethod
    def paint_faces(
        cls,
        bm: bmesh.types.BMesh,
        faces: List[bmesh.types.BMFace],
        color: Tuple[float, float, float, float],
        layer_name: str = "Col"
    ):
        """
        Paint faces with solid color.
        Color format: (R, G, B, A) - values 0.0-1.0
        """
        color_layer = cls.ensure_color_layer(bm, layer_name)
        
        for face in faces:
            for loop in face.loops:
                loop[color_layer] = color
    
    @classmethod
    def paint_all(
        cls,
        bm: bmesh.types.BMesh,
        color: Tuple[float, float, float, float],
        layer_name: str = "Col"
    ):
        """Paint entire mesh with single color"""
        cls.paint_faces(bm, list(bm.faces), color, layer_name)
    
    @classmethod
    def paint_by_normal(
        cls,
        bm: bmesh.types.BMesh,
        direction: Vector,
        color: Tuple[float, float, float, float],
        threshold: float = 0.7,
        layer_name: str = "Col"
    ):
        """Paint faces pointing in specified direction"""
        faces = AtomicOps.select_faces_by_normal(bm, direction, threshold)
        cls.paint_faces(bm, faces, color, layer_name)
    
    @classmethod
    def paint_by_height(
        cls,
        bm: bmesh.types.BMesh,
        colors: List[Tuple[float, Tuple[float, float, float, float]]],
        layer_name: str = "Col"
    ):
        """
        Paint based on vertex height (Z position).
        colors: List of (height_threshold, color) tuples, sorted by height
        """
        color_layer = cls.ensure_color_layer(bm, layer_name)
        
        for face in bm.faces:
            center_z = face.calc_center_median().z
            
            chosen_color = colors[0][1] if colors else (1, 1, 1, 1)
            for threshold, color in colors:
                if center_z >= threshold:
                    chosen_color = color
            
            for loop in face.loops:
                loop[color_layer] = chosen_color
    
    @classmethod
    def paint_gradient_vertical(
        cls,
        bm: bmesh.types.BMesh,
        color_bottom: Tuple[float, float, float, float],
        color_top: Tuple[float, float, float, float],
        layer_name: str = "Col"
    ):
        """Paint vertical gradient from bottom to top"""
        color_layer = cls.ensure_color_layer(bm, layer_name)
        
        min_z = min(v.co.z for v in bm.verts)
        max_z = max(v.co.z for v in bm.verts)
        height_range = max_z - min_z if max_z > min_z else 1.0
        
        for face in bm.faces:
            for loop in face.loops:
                t = (loop.vert.co.z - min_z) / height_range
                
                r = color_bottom[0] + (color_top[0] - color_bottom[0]) * t
                g = color_bottom[1] + (color_top[1] - color_bottom[1]) * t
                b = color_bottom[2] + (color_top[2] - color_bottom[2]) * t
                a = color_bottom[3] + (color_top[3] - color_bottom[3]) * t
                
                loop[color_layer] = (r, g, b, a)


class ColorPalette:
    """Predefined color palettes for character parts"""
    
    ARMOR_BLUE = (0.2, 0.4, 0.8, 1.0)
    ARMOR_SILVER = (0.7, 0.7, 0.75, 1.0)
    ARMOR_GOLD = (0.8, 0.65, 0.2, 1.0)
    ARMOR_DARK = (0.15, 0.15, 0.2, 1.0)
    
    ROBE_GREEN = (0.2, 0.6, 0.3, 1.0)
    ROBE_RED = (0.7, 0.15, 0.15, 1.0)
    ROBE_PURPLE = (0.5, 0.2, 0.6, 1.0)
    ROBE_BROWN = (0.4, 0.25, 0.15, 1.0)
    
    SKIN_LIGHT = (0.9, 0.75, 0.65, 1.0)
    SKIN_MEDIUM = (0.7, 0.5, 0.4, 1.0)
    SKIN_DARK = (0.35, 0.25, 0.2, 1.0)
    
    LEATHER_BROWN = (0.35, 0.2, 0.1, 1.0)
    LEATHER_BLACK = (0.1, 0.08, 0.08, 1.0)
    
    CLOTH_WHITE = (0.9, 0.9, 0.88, 1.0)
    CLOTH_BLACK = (0.1, 0.1, 0.12, 1.0)
    
    METAL_STEEL = (0.5, 0.5, 0.55, 1.0)
    METAL_BRONZE = (0.6, 0.4, 0.2, 1.0)
    METAL_COPPER = (0.7, 0.45, 0.3, 1.0)
    
    @classmethod
    def get_palette(cls, name: str) -> Tuple[float, float, float, float]:
        """Get color by name"""
        return getattr(cls, name.upper(), cls.CLOTH_WHITE)


class HardSurfaceKitbash:
    """
    Hard-Surface Kitbash Module
    
    Creates armor, equipment details by modifying mesh topology.
    Uses Inset+Extrude on selected faces instead of importing external assets.
    """
    
    @classmethod
    def add_armor_plate(
        cls,
        obj: bpy.types.Object,
        direction: Vector,
        thickness: float = 0.01,
        extrude: float = 0.02,
        color: Tuple[float, float, float, float] = ColorPalette.ARMOR_BLUE,
        threshold: float = 0.5
    ):
        """
        Add armor plate to faces pointing in direction.
        Insets and extrudes to create thickness, then paints.
        """
        bm = AtomicOps.get_bmesh(obj)
        
        faces = AtomicOps.select_faces_by_normal(bm, direction, threshold)
        
        if faces:
            new_faces = AtomicOps.inset_extrude(
                bm, faces, 
                inset_thickness=thickness,
                extrude_depth=extrude
            )
            
            VertexColorOps.paint_faces(bm, new_faces, color)
        
        AtomicOps.apply_bmesh(bm, obj)
    
    @classmethod
    def add_chest_armor(
        cls,
        obj: bpy.types.Object,
        armor_color: Tuple[float, float, float, float] = ColorPalette.ARMOR_BLUE,
        trim_color: Tuple[float, float, float, float] = ColorPalette.ARMOR_GOLD
    ):
        """Add chest plate armor to torso"""
        bm = AtomicOps.get_bmesh(obj)
        
        front_faces = AtomicOps.select_faces_by_normal(bm, Vector((0, -1, 0)), 0.3)
        
        upper_front = [f for f in front_faces if f.calc_center_median().z > 0]
        
        if upper_front:
            AtomicOps.inset_faces(bm, upper_front, thickness=0.005)
            bm.faces.ensure_lookup_table()
            
            center_faces = [f for f in bm.faces if f.is_valid and 
                           abs(f.calc_center_median().x) < 0.05 and
                           f.calc_center_median().z > 0.1]
            
            if center_faces:
                new_faces = AtomicOps.extrude_faces(bm, center_faces, offset=0.025)
                VertexColorOps.paint_faces(bm, new_faces, armor_color)
        
        AtomicOps.apply_bmesh(bm, obj)
    
    @classmethod
    def add_shoulder_pads(
        cls,
        obj: bpy.types.Object,
        color: Tuple[float, float, float, float] = ColorPalette.ARMOR_BLUE
    ):
        """Add shoulder pad armor"""
        bm = AtomicOps.get_bmesh(obj)
        
        up_faces = AtomicOps.select_faces_by_normal(bm, Vector((0, 0, 1)), 0.6)
        shoulder_faces = [f for f in up_faces if abs(f.calc_center_median().x) > 0.08]
        
        if shoulder_faces:
            new_faces = AtomicOps.inset_extrude(
                bm, shoulder_faces,
                inset_thickness=0.008,
                extrude_depth=0.03
            )
            VertexColorOps.paint_faces(bm, new_faces, color)
        
        AtomicOps.apply_bmesh(bm, obj)
    
    @classmethod
    def add_belt(
        cls,
        obj: bpy.types.Object,
        height: float,
        width: float = 0.03,
        color: Tuple[float, float, float, float] = ColorPalette.LEATHER_BROWN
    ):
        """Add belt around waist"""
        bm = AtomicOps.get_bmesh(obj)
        
        min_z = height - width / 2
        max_z = height + width / 2
        
        belt_faces = []
        for face in bm.faces:
            center = face.calc_center_median()
            if min_z <= center.z <= max_z:
                belt_faces.append(face)
        
        if belt_faces:
            new_faces = AtomicOps.extrude_faces(bm, belt_faces, offset=0.015)
            VertexColorOps.paint_faces(bm, new_faces, color)
        
        AtomicOps.apply_bmesh(bm, obj)
    
    @classmethod
    def add_gauntlets(
        cls,
        obj: bpy.types.Object,
        color: Tuple[float, float, float, float] = ColorPalette.ARMOR_BLUE
    ):
        """Add armored gauntlets to forearms"""
        bm = AtomicOps.get_bmesh(obj)
        
        arm_faces = []
        for face in bm.faces:
            center = face.calc_center_median()
            if abs(center.x) > 0.2 and center.z > 0.8 and center.z < 1.2:
                arm_faces.append(face)
        
        if arm_faces:
            new_faces = AtomicOps.inset_extrude(
                bm, arm_faces,
                inset_thickness=0.005,
                extrude_depth=0.012
            )
            VertexColorOps.paint_faces(bm, new_faces, color)
        
        AtomicOps.apply_bmesh(bm, obj)
    
    @classmethod
    def add_knee_pads(
        cls,
        obj: bpy.types.Object,
        color: Tuple[float, float, float, float] = ColorPalette.ARMOR_BLUE
    ):
        """Add knee pad armor"""
        bm = AtomicOps.get_bmesh(obj)
        
        knee_faces = []
        for face in bm.faces:
            center = face.calc_center_median()
            if 0.4 < center.z < 0.6 and face.normal.y < -0.3:
                knee_faces.append(face)
        
        if knee_faces:
            new_faces = AtomicOps.inset_extrude(
                bm, knee_faces,
                inset_thickness=0.01,
                extrude_depth=0.02
            )
            VertexColorOps.paint_faces(bm, new_faces, color)
        
        AtomicOps.apply_bmesh(bm, obj)


class CharacterPainter:
    """
    High-level character painting operations.
    Paints different body parts with appropriate colors.
    """
    
    @classmethod
    def paint_humanoid_base(
        cls,
        root_obj: bpy.types.Object,
        skin_color: Tuple[float, float, float, float] = ColorPalette.SKIN_LIGHT
    ):
        """Paint base skin color on all parts"""
        for child in root_obj.children:
            if child.type == 'MESH':
                bm = AtomicOps.get_bmesh(child)
                VertexColorOps.paint_all(bm, skin_color)
                AtomicOps.apply_bmesh(bm, child)
    
    @classmethod
    def paint_by_part(
        cls,
        root_obj: bpy.types.Object,
        part_colors: Dict[str, Tuple[float, float, float, float]]
    ):
        """
        Paint different colors per body part.
        part_colors: {"Head": color, "Torso": color, etc.}
        """
        for child in root_obj.children:
            if child.type == 'MESH':
                for part_name, color in part_colors.items():
                    if part_name.lower() in child.name.lower():
                        bm = AtomicOps.get_bmesh(child)
                        VertexColorOps.paint_all(bm, color)
                        AtomicOps.apply_bmesh(bm, child)
                        break
    
    @classmethod
    def apply_armor_set(
        cls,
        root_obj: bpy.types.Object,
        armor_color: Tuple[float, float, float, float] = ColorPalette.ARMOR_BLUE,
        undersuit_color: Tuple[float, float, float, float] = ColorPalette.CLOTH_BLACK
    ):
        """Apply full armor set to character"""
        for child in root_obj.children:
            if child.type != 'MESH':
                continue
            
            name_lower = child.name.lower()
            
            bm = AtomicOps.get_bmesh(child)
            VertexColorOps.paint_all(bm, undersuit_color)
            AtomicOps.apply_bmesh(bm, child)
            
            if 'torso' in name_lower:
                HardSurfaceKitbash.add_chest_armor(child, armor_color)
            elif 'arm' in name_lower:
                HardSurfaceKitbash.add_shoulder_pads(child, armor_color)
                HardSurfaceKitbash.add_gauntlets(child, armor_color)
            elif 'leg' in name_lower:
                HardSurfaceKitbash.add_knee_pads(child, armor_color)
    
    @classmethod
    def apply_robe(
        cls,
        root_obj: bpy.types.Object,
        robe_color: Tuple[float, float, float, float] = ColorPalette.ROBE_GREEN,
        trim_color: Tuple[float, float, float, float] = ColorPalette.ARMOR_GOLD
    ):
        """Apply robe/mage outfit to character"""
        for child in root_obj.children:
            if child.type != 'MESH':
                continue
            
            name_lower = child.name.lower()
            
            if 'head' in name_lower or 'hand' in name_lower:
                bm = AtomicOps.get_bmesh(child)
                VertexColorOps.paint_all(bm, ColorPalette.SKIN_LIGHT)
                AtomicOps.apply_bmesh(bm, child)
            elif 'torso' in name_lower or 'leg' in name_lower:
                bm = AtomicOps.get_bmesh(child)
                VertexColorOps.paint_all(bm, robe_color)
                
                bottom_faces = AtomicOps.select_faces_by_normal(bm, Vector((0, 0, -1)), 0.5)
                VertexColorOps.paint_faces(bm, bottom_faces, trim_color)
                
                AtomicOps.apply_bmesh(bm, child)
            elif 'arm' in name_lower:
                bm = AtomicOps.get_bmesh(child)
                VertexColorOps.paint_gradient_vertical(
                    bm, robe_color, ColorPalette.SKIN_LIGHT
                )
                AtomicOps.apply_bmesh(bm, child)
            elif 'foot' in name_lower or 'feet' in name_lower:
                bm = AtomicOps.get_bmesh(child)
                VertexColorOps.paint_all(bm, ColorPalette.LEATHER_BROWN)
                AtomicOps.apply_bmesh(bm, child)
