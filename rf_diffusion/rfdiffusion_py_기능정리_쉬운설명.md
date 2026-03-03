# rfdiffusion `.py` 파일 설명 (쉬운 버전 + 추가 설명)

기준 경로: `C:\project\sim_pip\RFdiffusion\rfdiffusion`

## 0) 먼저 큰 그림

RFdiffusion의 `.py`는 크게 4파트입니다.

1. 모델 본체(두뇌)
- 단백질 구조를 예측/생성하는 신경망 블록

2. 디퓨전 엔진
- 노이즈를 넣고 빼면서 구조를 샘플링하는 핵심 알고리즘

3. 입력/좌표/화학 유틸
- contig 해석, 좌표 변환, 아미노산/원자 정보 처리

4. 추론 실행/가이딩
- 실제 샘플 생성 루프, 대칭 처리, potential(유도 힘) 적용

---

## 1) 루트 `.py` 파일별 설명

### `RoseTTAFoldModel.py`
- 한 줄 역할: RFdiffusion 메인 모델 조립 파일
- 쉽게 말해: 여러 블록(임베딩/트랙/보조헤드)을 붙여 “실제 두뇌”를 만듭니다.
- 주로 볼 때: 모델 구조를 바꾸거나 차원을 조정할 때

### `Track_module.py`
- 한 줄 역할: MSA/Pair/Structure 3-track 업데이트 블록
- 쉽게 말해: 서열 정보, residue 간 관계, 3D 구조 정보를 서로 주고받으며 갱신
- 주로 볼 때: 성능 튜닝, block 동작 이해

### `Attention_module.py`
- 한 줄 역할: attention/FFN 등 공통 트랜스포머 레이어
- 쉽게 말해: “어떤 residue가 어떤 residue를 참고할지” 계산하는 기초 부품
- 주로 볼 때: attention 구조 수정

### `Embeddings.py`
- 한 줄 역할: 입력 특징(서열/위치/템플릿)을 모델이 먹기 좋은 벡터로 변환
- 쉽게 말해: raw 입력을 모델 언어로 번역
- 주로 볼 때: 입력 특징 추가/제거

### `SE3_network.py`
- 한 줄 역할: SE(3)-Transformer 래퍼
- 쉽게 말해: 회전/이동에 일관된(등변) 방식으로 3D 좌표를 다루는 블록
- 주로 볼 때: SE3 파라미터/백엔드 변경

### `AuxiliaryPredictor.py`
- 한 줄 역할: 거리/각도/토큰/LDDT 같은 보조 예측 헤드
- 쉽게 말해: 모델이 학습/추론 중 참고할 추가 출력
- 주로 볼 때: 보조 로스/출력 디버깅

### `diffusion.py`
- 한 줄 역할: 디퓨전 수식/스케줄/샘플 단계
- 쉽게 말해: 구조를 망가뜨렸다가 복원하는 절차를 정의하는 핵심 엔진
- 주로 볼 때: `T`, noise schedule, partial diffusion 관련 수정

### `igso3.py`
- 한 줄 역할: SO(3) 회전 디퓨전 수학 유틸
- 쉽게 말해: 좌표 중에서도 “회전” 노이즈를 처리하는 전문 모듈
- 주로 볼 때: 회전 관련 안정성/성능 이슈 분석

### `contigs.py`
- 한 줄 역할: contig 문자열 파싱 및 인덱스 매핑
- 쉽게 말해: `'A1-100/0 70-100'` 같은 명령을 모델 내부 인덱스로 바꿔줌
- 주로 볼 때: motif scaffolding/ppi 설정 디버깅

### `kinematics.py`
- 한 줄 역할: 거리/각도/좌표 변환 기하 유틸
- 쉽게 말해: 원자 좌표를 기하 특징으로 바꾸고 다시 다루는 도구 상자
- 주로 볼 때: 기하 feature 계산 검증

### `coords6d.py`
- 한 줄 역할: 3D 좌표 -> 6D 관계 특징 변환
- 쉽게 말해: residue 간 거리/각도 정보를 모델 입력용 2D 맵 형태로 생성
- 주로 볼 때: 구조 표현 방식 확인

### `chemical.py`
- 한 줄 역할: 아미노산/원자 이름/인덱스 상수 정의
- 쉽게 말해: 단백질 화학 사전(dictionary)
- 주로 볼 때: 원자 매핑 오류, residue 인코딩 확인

### `scoring.py`
- 한 줄 역할: 원자 타입 기반 스코어링 상수/함수
- 쉽게 말해: 물리/통계적 점수 계산용 테이블과 로직
- 주로 볼 때: 에너지/스코어 관련 분석

### `util.py`
- 한 줄 역할: 범용 유틸 (PDB 출력, 기하 계산 등)
- 쉽게 말해: 여기저기서 공통으로 쓰는 실무 함수 모음
- 주로 볼 때: 출력 파일 형식, 공통 함수 버그

### `util_module.py`
- 한 줄 역할: 모델 쪽 공통 유틸 (초기화, 그래프/좌표 helper)
- 쉽게 말해: 네트워크 블록 구현을 도와주는 보조 함수 집합
- 주로 볼 때: 레이어 초기화/그래프 처리 디버깅

### `model_input_logger.py`
- 한 줄 역할: 함수 입력 인자를 pickle로 기록하는 디버그 도구
- 쉽게 말해: “모델에 실제로 뭐가 들어갔는지” 캡처
- 주로 볼 때: 재현 어려운 버그 추적

### `__init__.py`
- 한 줄 역할: 패키지 초기화
- 쉽게 말해: Python import 경로를 맞추는 파일

---

## 2) `inference/` 하위 파일

### `inference/model_runners.py`
- 역할: 샘플러 초기화, 체크포인트 로딩, 추론 단계 실행
- 쉽게 말해: `run_inference.py`가 실제로 호출하는 “실행 총괄자”
- 중요도: 매우 높음 (실행 흐름 이해 핵심)

### `inference/utils.py`
- 역할: 추론 중 공통 함수(프레임 업데이트, 파싱/변환)
- 쉽게 말해: model_runners를 지원하는 실무 함수 모음

### `inference/symmetry.py`
- 역할: 대칭(Cn, Dn, tetra/octa/icosa) 처리
- 쉽게 말해: 대칭 복합체를 만들 때 회전/복제 규칙 담당

### `inference/__init__.py`
- 역할: 서브패키지 초기화

---

## 3) `potentials/` 하위 파일

### `potentials/potentials.py`
- 역할: `monomer_ROG`, `olig_contacts` 등 가이딩 potential 구현
- 쉽게 말해: 생성 구조가 원하는 방향(더 조밀/더 접촉)으로 가게 유도

### `potentials/manager.py`
- 역할: 사용자 문자열 설정을 potential 객체로 해석/관리
- 쉽게 말해: config 문자열을 실제 계산 모듈로 연결하는 어댑터

### `potentials/__init__.py`
- 역할: 서브패키지 초기화

---

## 4) 실전에서 자주 건드리는 파일 순서

1. `config/inference/base.yaml` (설정 변경)
2. `scripts/run_inference.py` (실행 방식 확인)
3. `rfdiffusion/inference/model_runners.py` (실제 샘플링 흐름)
4. 필요 시
   - contig 이슈: `rfdiffusion/contigs.py`
   - 대칭 이슈: `rfdiffusion/inference/symmetry.py`
   - potential 이슈: `rfdiffusion/potentials/potentials.py`

---

## 5) 빠른 한줄 요약

- `rfdiffusion`은 입력 조건(contig/타깃)을 해석하고,
- 디퓨전 엔진으로 구조를 샘플링하고,
- 필요하면 대칭/포텐셜 가이딩을 적용해,
- 최종 단백질 구조(PDB)를 내보내는 핵심 패키지입니다.
