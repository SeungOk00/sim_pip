# make_secstruc_adj.py 기능/입출력 정리

대상 파일: `C:\project\sim_pip\RFdiffusion\helper_scripts\make_secstruc_adj.py`

## 1) 이 스크립트의 기능

`make_secstruc_adj.py`는 PDB 구조 파일에서 RFdiffusion의 scaffold-guided 설계에 쓰는 특징 파일 2종을 생성하는 전처리 스크립트입니다.

생성하는 파일:
- `*_ss.pt`: residue별 2차구조 라벨 텐서
- `*_adj.pt`: 2차구조 블록 간 인접(접촉) 행렬 텐서

즉, `scaffoldguided.target_ss`, `scaffoldguided.target_adj`에 넣을 `.pt` 파일을 자동 생성합니다.

---

## 2) 입력 (Input)

CLI 인자:
- `--out_dir` (필수): 출력 폴더
- `--input_pdb` (선택): 단일 PDB 파일 경로
- `--pdb_dir` (선택): 여러 PDB가 있는 폴더 경로

제약:
- `--input_pdb`와 `--pdb_dir` 중 **하나만** 사용해야 합니다.

예시 1 (단일 PDB):
```bash
python helper_scripts/make_secstruc_adj.py \
  --input_pdb examples/input_pdbs/insulin_target.pdb \
  --out_dir examples/target_folds
```

예시 2 (폴더 일괄 처리):
```bash
python helper_scripts/make_secstruc_adj.py \
  --pdb_dir my_pdbs \
  --out_dir my_features
```

---

## 3) 출력 (Output)

입력 PDB 이름이 `name.pdb`이면 아래 두 파일이 생성됩니다.

1. `<name>_ss.pt`
- 타입: PyTorch tensor
- 길이: `L` (residue 수)
- 값 의미 (코드 기준):
  - `0 = Helix (H)`
  - `1 = Strand (E)`
  - `2 = Loop (L)`

2. `<name>_adj.pt`
- 타입: PyTorch tensor
- shape: `(L, L)`
- 의미:
  - 2차구조 segment(연속된 H/E/L 블록)끼리 Cβ 거리 기준으로 인접하면 1, 아니면 0
  - 기본 cutoff: `6 Å`
  - 기본 옵션에서 loop segment는 인접 계산에서 제외 (`include_loops=False`)

---

## 4) 내부 처리 흐름

1. PDB 로드 및 residue/좌표 파싱
2. 2차구조 추출
   - `pyrosetta` 사용 가능 시: DSSP 기반
   - 미설치 시: 내부 근사 함수(`get_sse`) 사용
3. 2차구조를 숫자 라벨로 변환 (`H/E/L -> 0/1/2`)
4. Cβ 좌표 기반 block adjacency matrix 계산
5. `*_ss.pt`, `*_adj.pt` 저장

---

## 5) 참고 사항

- 실행 시 `pyrosetta`가 없으면 경고가 출력되며 근사 SSE 계산으로 대체됩니다.
- scaffold-guided 예제(`design_ppi_scaffolded.sh`)에서 사용하는 `target_ss`, `target_adj` 파일을 직접 만드는 용도입니다.
