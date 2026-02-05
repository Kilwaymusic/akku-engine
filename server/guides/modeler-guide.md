# 2권: Modeler Guide - SDK 활용 및 Python 코드 생성
대상: Blender CLI 코드 작성 (Technician Persona)

## Blender CLI 절대 원칙 (Headless Safe)
1. **bpy.ops 금지** - 반드시 bmesh로 직접 조작
2. **Object Isolation** - Body, Hair, Armor를 별도 객체로 생성

## 핵심 SDK 함수

### 유기적 형태 생성
```python
# 팔다리 - 끝으로 갈수록 가늘어지는 원기둥
add_tapered_cylinder(bm, pos, radius_bottom, radius_top, height, segments)

# 머리/관절 - 부드러운 구체
add_icosphere(bm, pos, radius, subdivisions=2)

# 정점 부드럽게
smooth_vertices(bm, verts, factor=0.5)
```

### 관절 토폴로지
```python
# 무릎/팔꿈치에 최소 3개 면 분할
subdivide_mesh(bm, cuts=2)
```

### 캐비티 모델링 (눈, 장식)
```python
# 표면에 홈을 파서 '떠있는 느낌' 제거
inset_and_extrude(bm, face, inset_amt=0.03, extrude_depth=-0.05)
```

## 메시 최종화 파이프라인
```python
# 1. 모든 객체를 하나로 병합
merge_all_objects_to_one()

# 2. 유기적 마무리 (remesh + smooth)
finalize_organic_mesh(obj, voxel_size=0.03, smooth_iterations=2)

# 3. 필수 정리
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.001)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
```

## 위상 규칙
- 모든 메시는 닫힌 구조(Manifold)
- 생성 마지막에 merge_close_verts() + recalculate_normals() 호출
