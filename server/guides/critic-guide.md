# 3권: Critic Guide - 시각 비평 및 자가 수정
대상: 스크린샷 분석 및 피드백 (Evaluator Persona)

## 3면 분석 체크리스트 (Tri-View Rule)

### Front View
- 좌우 대칭성
- 이목구비 위치
- 전체 비율

### Side View
- 신체 두께감(Z축)
- 장식물이 몸통에 제대로 부착되었는지

### Wireframe View
- 스파이크(찌그러짐) 현상
- 구멍(Hole) 유무

## 데이터 오류 판별 기준

| 오류 유형 | 증상 | 수정 방법 |
|-----------|------|-----------|
| Spike | 정점이 비정상적으로 뻗어나옴 | extrude 수치 또는 weight 값 수정 |
| Floating | 장비가 몸체에서 떨어짐 | location 좌표값 미세 조절 |
| Muddy Color | 색상이 의도보다 어두움 | roughness 낮추거나 metallic 조절 |
| Blocky | 로봇/레고처럼 딱딱함 | add_icosphere/tapered_cylinder 사용, smooth 적용 |

## 자율 수정 전략 (Refinement Logic)

### 제한 규칙
- 한 번에 최대 2개 항목만 수정 (전체 구조 흔들림 방지)

### Incremental Fix 예시
- "팔이 짧다" → 기존 length * 1.2 (상대적 수정)
- "머리가 작다" → headScale * 1.15
- "너무 딱딱하다" → smooth_iterations 증가, voxel_size 감소

### 품질 체크 우선순위
1. 실루엣 (전체적인 형태가 캐릭터답게 보이는가?)
2. 비율 (머리, 몸통, 팔다리 비율이 자연스러운가?)
3. 디테일 (장비, 색상이 프롬프트와 일치하는가?)
