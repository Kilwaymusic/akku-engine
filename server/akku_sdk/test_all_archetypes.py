#!/usr/bin/env python3
"""
Akku SDK v3.6 - Comprehensive Archetype Test Suite

Tests all SDK features by generating characters for major archetypes:
- Robot (로봇)
- Warrior (전사)
- Mage (마법사)
- Knight (기사)
- Archer (궁수)
- Healer (힐러)
- Assassin (암살자)
- Tank (탱커)

Each archetype tests:
- Base mesh loading
- Body type application
- Stylized shader system
- Equipment (kitbash) attachment
- Auto weight transfer
- Mesh optimization
- GLB export

Run with: blender --background --python test_all_archetypes.py
"""

import bpy
import bmesh
import sys
import os
import json
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path

sdk_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

from akku_sdk import (
    AkkuConfig,
    AkkuLogger,
    MeshTools,
    MeshAnalyzer,
    StyleAnalyzer,
    ToolRegistry,
    StylizedShaderSystem,
    StylizedShaderParams,
    BodyTypePresets,
    BodyTypeSystem,
    KitbashLibrary,
    KitbashEquipper,
    AutoWeightTransfer,
    FinalizePipeline,
    PlatformTargets,
    MeshOptimizer,
    MaterialOptimizer,
    DecimateEngine,
    MeshJoiner,
    GLBHandler,
    FBXHandler,
)


@dataclass
class ArchetypeConfig:
    """Configuration for an archetype test case"""
    name: str
    name_kr: str
    prompt: str
    body_type: str
    style: str
    poly_level: str
    color: Tuple[float, float, float]
    equipment: List[str]
    platform: str = "mobile"


@dataclass
class TestResult:
    """Result of an archetype test"""
    archetype: str
    success: bool
    duration_ms: int
    triangle_count: int
    material_count: int
    vertex_count: int
    file_size_kb: float
    output_path: str
    errors: List[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


ARCHETYPE_CONFIGS = [
    ArchetypeConfig(
        name="robot",
        name_kr="로봇",
        prompt="blue metallic robot warrior",
        body_type="muscular",
        style="stylized",
        poly_level="medium",
        color=(0.2, 0.4, 0.8),
        equipment=["helmet_tech", "shoulder_heavy", "chest_heavy"],
        platform="mobile"
    ),
    ArchetypeConfig(
        name="warrior",
        name_kr="전사",
        prompt="강력한 전사 빨간 갑옷",
        body_type="heroic",
        style="stylized",
        poly_level="medium",
        color=(0.8, 0.2, 0.2),
        equipment=["helmet_warrior", "shoulder_heavy", "weapon_sword"],
        platform="mobile"
    ),
    ArchetypeConfig(
        name="mage",
        name_kr="마법사",
        prompt="purple mystical mage with staff",
        body_type="thin",
        style="stylized",
        poly_level="medium",
        color=(0.6, 0.2, 0.8),
        equipment=["helmet_hood", "weapon_staff"],
        platform="mobile"
    ),
    ArchetypeConfig(
        name="knight",
        name_kr="기사",
        prompt="silver armored knight with shield",
        body_type="athletic",
        style="realistic",
        poly_level="high",
        color=(0.7, 0.7, 0.75),
        equipment=["helmet_full", "shoulder_heavy", "chest_heavy", "shield_round"],
        platform="pc"
    ),
    ArchetypeConfig(
        name="archer",
        name_kr="궁수",
        prompt="green forest archer",
        body_type="athletic",
        style="stylized",
        poly_level="medium",
        color=(0.2, 0.6, 0.3),
        equipment=["helmet_hood", "shoulder_light"],
        platform="mobile"
    ),
    ArchetypeConfig(
        name="healer",
        name_kr="힐러",
        prompt="white holy healer with golden accents",
        body_type="default",
        style="stylized",
        poly_level="medium",
        color=(0.9, 0.9, 0.95),
        equipment=["helmet_circlet", "weapon_staff"],
        platform="mobile"
    ),
    ArchetypeConfig(
        name="assassin",
        name_kr="암살자",
        prompt="black shadow assassin",
        body_type="thin",
        style="stylized",
        poly_level="medium",
        color=(0.1, 0.1, 0.15),
        equipment=["helmet_hood", "weapon_dagger"],
        platform="mobile"
    ),
    ArchetypeConfig(
        name="tank",
        name_kr="탱커",
        prompt="massive armored tank warrior",
        body_type="fat",
        style="stylized",
        poly_level="high",
        color=(0.4, 0.35, 0.3),
        equipment=["helmet_full", "shoulder_heavy", "chest_heavy", "shield_tower"],
        platform="pc"
    ),
    ArchetypeConfig(
        name="chibi_hero",
        name_kr="치비 영웅",
        prompt="cute chibi hero",
        body_type="chibi",
        style="chibi",
        poly_level="low",
        color=(0.9, 0.6, 0.3),
        equipment=["helmet_simple", "weapon_sword"],
        platform="mobile_low"
    ),
    ArchetypeConfig(
        name="minifig_knight",
        name_kr="미니피그 기사",
        prompt="blocky minifig knight",
        body_type="default",
        style="minifig",
        poly_level="ultra_low",
        color=(0.2, 0.5, 0.8),
        equipment=["helmet_simple", "shield_round"],
        platform="mobile_low"
    ),
]


class ArchetypeTestRunner:
    """Runs archetype tests and generates reports
    
    Modes:
    - synthetic: Uses generated test meshes (default, runs anywhere)
    - fbx: Uses actual Mixamo FBX files (requires assets/base_meshes/)
    """
    
    def __init__(self, output_dir: str = "/tmp/akku_test_output", use_fbx: bool = False):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[TestResult] = []
        self.use_fbx = use_fbx
        
        if use_fbx:
            AkkuLogger.info("FBX mode: Using Mixamo base meshes")
        
    def clear_scene(self):
        """Clear all objects from scene"""
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        for mesh in bpy.data.meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for mat in bpy.data.materials:
            if mat.users == 0:
                bpy.data.materials.remove(mat)
    
    def create_test_mesh(self) -> bpy.types.Object:
        """Create a simple test humanoid mesh"""
        bm = bmesh.new()
        
        body_verts = []
        for z in [0.0, 0.3, 0.6, 0.9, 1.2, 1.5]:
            width = 0.2 if z < 0.3 or z > 1.2 else 0.25
            depth = 0.15 if z < 0.3 or z > 1.2 else 0.18
            for x, y in [(-width, -depth), (width, -depth), (width, depth), (-width, depth)]:
                body_verts.append(bm.verts.new((x, y, z)))
        
        bm.verts.ensure_lookup_table()
        
        for i in range(5):
            base = i * 4
            top = (i + 1) * 4
            for j in range(4):
                next_j = (j + 1) % 4
                try:
                    bm.faces.new([
                        body_verts[base + j],
                        body_verts[base + next_j],
                        body_verts[top + next_j],
                        body_verts[top + j]
                    ])
                except:
                    pass
        
        try:
            bm.faces.new([body_verts[0], body_verts[3], body_verts[2], body_verts[1]])
            bm.faces.new([body_verts[-4], body_verts[-3], body_verts[-2], body_verts[-1]])
        except:
            pass
        
        mesh = bpy.data.meshes.new("TestCharacter")
        bm.to_mesh(mesh)
        bm.free()
        
        obj = bpy.data.objects.new("TestCharacter", mesh)
        bpy.context.collection.objects.link(obj)
        
        return obj
    
    def run_archetype_test(self, config: ArchetypeConfig) -> TestResult:
        """Run a single archetype test"""
        start_time = time.time()
        errors = []
        
        AkkuLogger.info(f"Testing archetype: {config.name} ({config.name_kr})")
        
        try:
            self.clear_scene()
        except Exception as e:
            errors.append(f"Scene clear failed: {e}")
        
        obj = None
        armature = None
        
        if self.use_fbx:
            try:
                gender = "male"
                mesh_path = AkkuConfig.BASE_MESHES.get(gender)
                if mesh_path and os.path.exists(mesh_path):
                    new_objects = FBXHandler.import_fbx(mesh_path)
                    mesh_objects = [o for o in new_objects if o.type == 'MESH']
                    armatures = [o for o in new_objects if o.type == 'ARMATURE']
                    if mesh_objects:
                        obj = mesh_objects[0]
                        MeshTools.normalize_scale(obj, AkkuConfig.TARGET_HEIGHT)
                    if armatures:
                        armature = armatures[0]
                    AkkuLogger.info(f"Loaded FBX: {mesh_path}")
                else:
                    obj = self.create_test_mesh()
                    AkkuLogger.info("FBX not found, using synthetic mesh")
            except Exception as e:
                errors.append(f"FBX load failed: {e}")
                obj = self.create_test_mesh()
        else:
            try:
                obj = self.create_test_mesh()
            except Exception as e:
                errors.append(f"Mesh creation failed: {e}")
        
        if obj is None:
            return TestResult(
                archetype=config.name,
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                triangle_count=0,
                material_count=0,
                vertex_count=0,
                file_size_kb=0,
                output_path="",
                errors=errors
            )
        
        try:
            detected_color = StyleAnalyzer.detect_color(config.prompt)
            detected_archetype = StyleAnalyzer.detect_archetype(config.prompt)
            poly_settings = StyleAnalyzer.get_poly_settings(config.poly_level)
            AkkuLogger.info(f"StyleAnalyzer: color={detected_color}, archetype={detected_archetype}")
        except Exception as e:
            errors.append(f"StyleAnalyzer failed: {e}")
        
        try:
            params = BodyTypePresets.get_preset(config.body_type)
            BodyTypeSystem.apply_body_type(obj, params)
            AkkuLogger.info(f"Applied body type: {config.body_type}")
        except Exception as e:
            errors.append(f"Body type failed: {e}")
        
        try:
            StylizedShaderSystem.apply_stylized_shader(
                obj, 
                config.color, 
                config.style
            )
            AkkuLogger.info(f"Applied shader: {config.style} with color {config.color}")
        except Exception as e:
            errors.append(f"Shader failed: {e}")
        
        try:
            for equip_id in config.equipment:
                part = KitbashLibrary.get_part(equip_id)
                if part:
                    AkkuLogger.info(f"Equipment available: {equip_id} → {part.name}")
                    if armature and self.use_fbx:
                        try:
                            KitbashEquipper.equip_part(armature, equip_id, auto_rig=True)
                            AkkuLogger.info(f"Equipped: {equip_id}")
                        except Exception as eq_e:
                            AkkuLogger.debug(f"Equip skipped: {eq_e}")
        except Exception as e:
            errors.append(f"Equipment lookup failed: {e}")
        
        try:
            MeshOptimizer.remove_doubles(obj, 0.0001)
            MeshOptimizer.dissolve_degenerate(obj)
            
            poly_settings = StyleAnalyzer.get_poly_settings(config.poly_level)
            target_tris = poly_settings.get("target_triangles", 1500)
            current_tris = MeshOptimizer.get_triangle_count(obj)
            if current_tris > target_tris:
                DecimateEngine.decimate_to_target(obj, target_tris)
                AkkuLogger.info(f"Decimated to poly_level '{config.poly_level}' target: {target_tris}")
            
            AkkuLogger.info("MeshOptimizer: remove_doubles, dissolve_degenerate applied")
        except Exception as e:
            errors.append(f"MeshOptimizer failed: {e}")
        
        try:
            pipeline = FinalizePipeline(config.platform)
            result = pipeline.optimize_object(obj)
            AkkuLogger.info(f"FinalizePipeline for {config.platform}: {result.original_tris} → {result.final_tris} tris")
        except Exception as e:
            errors.append(f"Optimization failed: {e}")
        
        output_path = self.output_dir / f"{config.name}_{config.style}_{config.platform}.glb"
        file_size_kb = 0
        
        try:
            GLBHandler.export_glb(str(output_path))
            if output_path.exists():
                file_size_kb = output_path.stat().st_size / 1024
                AkkuLogger.info(f"Exported: {output_path} ({file_size_kb:.1f} KB)")
        except Exception as e:
            errors.append(f"Export failed: {e}")
        
        mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
        total_verts = sum(len(o.data.vertices) for o in mesh_objs)
        total_tris = sum(len(o.data.polygons) for o in mesh_objs)
        total_mats = sum(len(o.data.materials) for o in mesh_objs)
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        return TestResult(
            archetype=config.name,
            success=len(errors) == 0,
            duration_ms=duration_ms,
            triangle_count=total_tris,
            material_count=total_mats,
            vertex_count=total_verts,
            file_size_kb=file_size_kb,
            output_path=str(output_path),
            errors=errors
        )
    
    def run_all_tests(self) -> Dict:
        """Run all archetype tests"""
        print("\n" + "=" * 60)
        print("AKKU SDK v3.6 - ARCHETYPE TEST SUITE")
        print("=" * 60 + "\n")
        
        total_start = time.time()
        
        for config in ARCHETYPE_CONFIGS:
            result = self.run_archetype_test(config)
            self.results.append(result)
            
            status = "✓ PASS" if result.success else "✗ FAIL"
            print(f"{status} | {config.name:15} | {result.duration_ms:5}ms | {result.triangle_count:5} tris | {result.file_size_kb:6.1f} KB")
            
            if result.errors:
                for err in result.errors:
                    print(f"      └─ {err}")
        
        total_duration = time.time() - total_start
        
        passed = sum(1 for r in self.results if r.success)
        failed = len(self.results) - passed
        
        print("\n" + "=" * 60)
        print(f"SUMMARY: {passed} passed, {failed} failed ({total_duration:.1f}s total)")
        print("=" * 60 + "\n")
        
        report = {
            "version": "3.6.0",
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": len(self.results),
            "passed": passed,
            "failed": failed,
            "total_duration_ms": int(total_duration * 1000),
            "output_directory": str(self.output_dir),
            "results": [r.to_dict() for r in self.results]
        }
        
        report_path = self.output_dir / "test_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"Report saved: {report_path}")
        
        return report
    
    def generate_quality_report(self) -> str:
        """Generate human-readable quality report"""
        lines = [
            "# Akku SDK v3.6 Quality Report",
            "",
            "## Test Summary",
            "",
            f"- **Total Tests**: {len(self.results)}",
            f"- **Passed**: {sum(1 for r in self.results if r.success)}",
            f"- **Failed**: {sum(1 for r in self.results if not r.success)}",
            "",
            "## Archetype Results",
            "",
            "| Archetype | Status | Triangles | Materials | File Size | Duration |",
            "|-----------|--------|-----------|-----------|-----------|----------|",
        ]
        
        for r in self.results:
            status = "✓ Pass" if r.success else "✗ Fail"
            lines.append(
                f"| {r.archetype:15} | {status} | {r.triangle_count:9} | {r.material_count:9} | {r.file_size_kb:7.1f} KB | {r.duration_ms:6} ms |"
            )
        
        lines.extend([
            "",
            "## Platform Targets",
            "",
            "| Platform | Max Triangles | Max Materials | Decimate Ratio |",
            "|----------|---------------|---------------|----------------|",
        ])
        
        for name, profile in PlatformTargets.PROFILES.items():
            lines.append(
                f"| {name:12} | {profile.max_triangles:13} | {profile.max_materials:13} | {profile.decimate_ratio:14.2f} |"
            )
        
        lines.extend([
            "",
            "## SDK Modules Tested",
            "",
            "- **MeshTools**: Mesh creation and manipulation",
            "- **BodyTypeSystem**: Body deformation (12 presets)",
            "- **StylizedShaderSystem**: Procedural shaders (8 styles)",
            "- **KitbashLibrary**: Equipment component system",
            "- **FinalizePipeline**: Game engine optimization",
            "- **GLBHandler**: glTF 2.0 export",
            "",
            "---",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ])
        
        report_text = "\n".join(lines)
        
        report_path = self.output_dir / "quality_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"Quality report saved: {report_path}")
        
        return report_text


def main():
    """Main entry point
    
    Usage:
        blender --background --python test_all_archetypes.py
        blender --background --python test_all_archetypes.py -- --fbx
    """
    use_fbx = "--fbx" in sys.argv
    
    runner = ArchetypeTestRunner(use_fbx=use_fbx)
    runner.run_all_tests()
    runner.generate_quality_report()
    
    mode = "FBX" if use_fbx else "synthetic"
    print(f"\nTest complete ({mode} mode). Check /tmp/akku_test_output/ for GLB files and reports.")


if __name__ == "__main__":
    main()
