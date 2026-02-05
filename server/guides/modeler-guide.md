# 2권: Modeler Guide - SDK 활용 및 Python 코드 생성
대상: Blender CLI 코드 작성 (Technician Persona)

## Blender CLI 절대 원칙 (Headless Safe)
1. **bpy.ops 금지** - 반드시 bmesh로 직접 조작
2. **Object Isolation** - Body, Hair, Armor를 별도 객체로 생성

## ANTHROPOMORPHIC(수인) 캐릭터 모델링

### 기본 구조 (여우, 늑대, 고양이 등)
```python
# 1. 머리: 기본 구체 + 주둥이
add_icosphere(bm, (0, 0, 1.6), 0.18, subdivisions=2)  # 머리
add_tapered_cylinder(bm, (0, 0.15, 1.55), 0.08, 0.04, 0.18, 8)  # 주둥이 (앞으로 돌출)

# 2. 귀: 위로 뾰족한 콘
add_cone(bm, (-0.12, -0.05, 1.82), 0.06, 0.15, 6)  # 왼쪽 귀
add_cone(bm, (0.12, -0.05, 1.82), 0.06, 0.15, 6)   # 오른쪽 귀

# 3. 꼬리: 테이퍼드 실린더 체인
add_tapered_cylinder(bm, (0, -0.25, 0.8), 0.08, 0.03, 0.4, 8)  # 꼬리
```

### 멀티톤 색상 (깊이감)
```python
# 기본 털색
mat_fur_base = create_material("FurBase", (0.55, 0.40, 0.28))  # 갈색
mat_fur_dark = create_material("FurDark", (0.35, 0.25, 0.18))  # 어두운 갈색 (등, 귀 끝)
mat_fur_light = create_material("FurLight", (0.75, 0.60, 0.45))  # 밝은 갈색 (배, 얼굴)
mat_accent = create_material("Accent", (0.9, 0.6, 0.2))  # 주황색 (눈, 코)
```

### 손가락 모델링
```python
# 손바닥
add_sphere(bm, (-0.35, 0, 0.5), 0.045, 8, 6)
# 손가락 4개 (테이퍼드 실린더)
for i, offset in enumerate([-0.03, -0.01, 0.01, 0.03]):
    add_tapered_cylinder(bm, (-0.35, offset, 0.42), 0.012, 0.008, 0.08, 6)
```

### 체형별 비율
| 체형 | 특징 | height | shoulderWidth | waistWidth |
|------|------|--------|---------------|------------|
| 마른 체형 | 가늘고 긴 사지 | 0.1 | 0.35 | 0.18 |
| 보통 체형 | 균형잡힌 비율 | 0.0 | 0.42 | 0.22 |
| 근육질 | 넓은 어깨, 좁은 허리 | 0.2 | 0.50 | 0.24 |

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
