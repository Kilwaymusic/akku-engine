# 2권: Modeler Guide - SDK 활용 및 Python 코드 생성
대상: Blender CLI 코드 작성 (Technician Persona)

## Blender CLI 절대 원칙 (Headless Safe)
1. **bpy.ops 금지** - 반드시 bmesh로 직접 조작
2. **Object Isolation** - Body, Hair, Armor를 별도 객체로 생성

---

## 핵심 마인드셋: "도형 배치" ❌ → "메시 조각" ✅

### 잘못된 접근법 (도형 배치)
```python
# ❌ 나쁜 예: 머리 위에 귀를 "얹음"
add_icosphere(bm, (0, 0, 1.6), 0.18)  # 머리
add_cone(bm, (0.1, 0, 1.85), 0.06, 0.15, 6)  # 귀를 위에 놓음
# 결과: 귀가 머리에서 떨어져 보임 (Floating)
```

### 올바른 접근법 (메시 조각 - Socket Modeling)
```python
# ✅ 좋은 예: 머리에서 귀를 "성장"시킴
add_icosphere(bm, (0, 0, 1.6), 0.18)  # 머리
# 귀가 나올 위치의 면을 찾아서 inset → extrude
ear_face = find_face_at_position(bm, (0.1, 0, 1.75))
bmesh.ops.inset_individual(bm, faces=[ear_face], thickness=0.02)  # 홈 생성
bmesh.ops.extrude_face_region(bm, geom=[ear_face])  # 귀 돌출
# 결과: 귀가 머리에 "심겨 있음"
```

---

## Socket Modeling 기법 (파내기)

### 원칙: "얹기" 대신 "파내기"
모든 디테일(눈, 귀, 주둥이)은 표면에 **얹지 말고**, 표면을 **파낸 후** 그 안에서 성장시킨다.

### 귀 모델링 (Socket 방식)
```python
def create_ear_from_head(bm, head_center, ear_pos, ear_height=0.15):
    # 1. 머리에서 귀 위치의 면 찾기
    ear_face = find_closest_face(bm, ear_pos)
    
    # 2. 홈(cavity) 생성 - inset으로 면을 좁힘
    inset_result = bmesh.ops.inset_individual(
        bm, faces=[ear_face], thickness=0.015, depth=0.01
    )
    
    # 3. 홈에서 귀 돌출 - extrude
    extruded = bmesh.ops.extrude_face_region(bm, geom=[ear_face])
    verts = [v for v in extruded['geom'] if isinstance(v, bmesh.types.BMVert)]
    
    # 4. 뾰족하게 끝내기 - 정점 모으기
    top_center = Vector(ear_pos) + Vector((0, 0, ear_height))
    bmesh.ops.pointmerge(bm, verts=verts, merge_co=top_center)
```

### 눈 모델링 (Inset 방식)
```python
def create_eye_cavity(bm, eye_pos, eye_radius=0.02):
    # 1. 눈 위치의 면 찾기
    eye_face = find_closest_face(bm, eye_pos)
    
    # 2. Inset으로 눈 테두리 생성
    bmesh.ops.inset_individual(bm, faces=[eye_face], thickness=eye_radius)
    
    # 3. 안쪽으로 파내기 (음수 extrude)
    bmesh.ops.extrude_face_region(bm, geom=[eye_face])
    move_verts(bm, eye_face.verts, direction=(0, -0.015, 0))  # 안쪽으로
```

### 주둥이 모델링 (연속 Extrude)
```python
def create_snout_from_face(bm, face_center, snout_length=0.15):
    # 1. 앞면에서 주둥이 영역 선택
    snout_faces = select_faces_in_radius(bm, face_center, radius=0.08)
    
    # 2. 연속 extrude로 주둥이 성장
    for i in range(3):
        scale = 1.0 - (i * 0.2)  # 점점 작아짐
        extruded = bmesh.ops.extrude_face_region(bm, geom=snout_faces)
        move_and_scale(bm, extruded, forward=snout_length/3, scale=scale)
```

---

## 관절 연결 보장 (Anti-Floating)

### 원칙: 모든 부위는 물리적으로 겹쳐야 함
```python
# ❌ 나쁜 예: 팔과 몸통이 떨어짐
add_cylinder(bm, shoulder_pos, ...)  # 몸통
add_cylinder(bm, (shoulder_pos[0] + 0.2, ...), ...)  # 팔 (gap 발생!)

# ✅ 좋은 예: 팔이 몸통에 겹침
add_cylinder(bm, shoulder_pos, ...)  # 몸통 (어깨까지 확장)
add_tapered_cylinder(bm, (shoulder_pos[0] + 0.05, ...), ...)  # 팔 (겹침!)
```

### 연결 검증 함수
```python
def verify_joint_connection(bm, joint_pos, min_overlap=0.02):
    """관절 위치에서 최소 겹침 거리 확인"""
    verts_near_joint = [v for v in bm.verts 
                        if (v.co - Vector(joint_pos)).length < min_overlap]
    if len(verts_near_joint) < 4:
        print(f"WARNING: Joint at {joint_pos} may be floating!")
        return False
    return True
```

---

## ANTHROPOMORPHIC(수인) 캐릭터 모델링

### 기본 구조 (여우, 늑대, 고양이 등) - Socket 방식
```python
# 1. 머리: 기본 구체
head_verts = add_icosphere(bm, (0, 0, 1.6), 0.18, subdivisions=2)

# 2. 주둥이: 앞면에서 extrude (얹지 않음!)
front_face = find_face_at_position(bm, (0, 0.15, 1.55))
create_snout_from_face(bm, front_face, length=0.15)

# 3. 귀: 머리 위에서 extrude (Socket 방식)
left_ear_face = find_face_at_position(bm, (-0.1, 0, 1.75))
create_ear_from_head(bm, left_ear_face, height=0.15)
right_ear_face = find_face_at_position(bm, (0.1, 0, 1.75))
create_ear_from_head(bm, right_ear_face, height=0.15)

# 4. 꼬리: 엉덩이에서 extrude
tail_face = find_face_at_position(bm, (0, -0.2, 0.85))
create_tail_from_hip(bm, tail_face, length=0.4)
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
