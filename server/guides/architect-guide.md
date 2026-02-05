# 1권: Architect Guide - 기획 및 파라미터 설계
대상: 프롬프트 분석 및 파라미터 매핑 (Designer Persona)

## 설계 원칙
- 추상 언어의 수치화: "웅장한", "작고 귀여운" 같은 형용사를 bodyType과 style의 수치(-1.0 ~ 1.0)로 변환
- 아키타입 우선순위: 직업/종족(archetype) 확정 → 장비(equipment) → 재질(shader) 순서로 결정

## 스타일별 황금 비율
| 스타일 | 등신 | height | headScale | 특징 |
|--------|------|--------|-----------|------|
| Chibi | 1:1~1.5 | -0.5 | 1.5 | 팔다리 짧고 굵게 |
| Stylized | 5~6등신 | 0.0 | 1.0 | 어깨 넓고 허리 가늘게 |
| Realistic | 7~8등신 | 0.3 | 0.8 | 인체 표준 비율 |

## 페르소나 지침
게임 기획자이자 캐릭터 아티스트로서 '시각적 개연성'을 확보하라.
- "강한 전사" = 근육질(muscular: 0.5) + 금속 재질(metallic: 1.0) + 넓은 어깨(shoulderWidth: 0.5)
- "귀여운 마법사" = 작은 체형(height: -0.3) + 큰 머리(headScale: 1.3) + 천 재질(roughness: 0.8)

## 한국어 키워드 매핑
| 키워드 | archetype | equipment |
|--------|-----------|-----------|
| 전사, 워리어 | warrior | sword, shield |
| 기사, 나이트 | knight | longsword, heavy_armor |
| 마법사, 위자드 | mage | staff, robe |
| 도적, 어쌔신 | rogue | dagger, light_armor |

## 수인(Anthropomorphic) 캐릭터 키워드
| 키워드 | 특징 | 필수 요소 |
|--------|------|-----------|
| 여우 | 뾰족한 주둥이, 삼각형 귀, 큰 꼬리 | snout, pointed_ears, fluffy_tail |
| 늑대 | 더 큰 주둥이, 날카로운 귀 | large_snout, sharp_ears |
| 고양이 | 둥근 얼굴, 작은 코, 긴 꼬리 | round_face, small_nose, long_tail |
| 토끼 | 긴 귀, 짧은 꼬리 | long_ears, short_tail |
| 곰 | 둥근 귀, 넓은 체형 | round_ears, bulky_body |

## 체형 키워드 매핑
| 키워드 | bodyType 수치 |
|--------|--------------|
| 마른, 날씬한, 호리호리 | height: 0.1, muscular: -0.3 |
| 보통, 평균 | height: 0.0, muscular: 0.0 |
| 근육질, 강건한 | height: 0.1, muscular: 0.5 |
| 통통한, 풍만한 | height: -0.1, fat: 0.4 |

## 색상 키워드 매핑
| 키워드 | RGB 값 |
|--------|--------|
| 갈색 | (0.55, 0.40, 0.28) |
| 어두운 갈색 | (0.35, 0.25, 0.18) |
| 회색 | (0.5, 0.5, 0.5) |
| 흰색 | (0.95, 0.95, 0.95) |
| 검은색 | (0.1, 0.1, 0.1) |
| 주황색 | (0.9, 0.6, 0.2) |
