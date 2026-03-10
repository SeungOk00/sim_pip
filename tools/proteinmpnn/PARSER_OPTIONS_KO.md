# ProteinMPNN 파서 옵션 정리

이 문서는 `protein_mpnn_run.py`의 argparse 옵션을 README 기준으로 한국어로 정리한 것입니다.

## 1) 실행/모델 기본 옵션

- `--suppress_print`:
  - 로그 출력 제어 (`0`: 출력, `1`: 최소 출력)
- `--ca_only`:
  - CA-only 구조를 파싱하고 CA-only 모델 사용
- `--path_to_model_weights`:
  - 모델 가중치 폴더 경로 직접 지정
- `--model_name`:
  - 사용할 모델 이름 (`v_48_002`, `v_48_010`, `v_48_020`, `v_48_030`)
- `--use_soluble_model`:
  - soluble 전용으로 학습된 가중치 사용
- `--seed`:
  - 랜덤 시드 (`0`이면 랜덤으로 선택)

## 2) 출력/평가 관련 옵션

- `--save_score`:
  - 샘플된 서열의 점수(-log_prob) 저장 여부
- `--path_to_fasta`:
  - FASTA 서열 입력 경로(점수 계산용)
- `--save_probs`:
  - 위치별 아미노산 확률 저장 여부
- `--score_only`:
  - 서열 생성 없이 점수만 계산
- `--conditional_probs_only`:
  - p(s_i | 나머지 서열 + 백본)만 계산
- `--conditional_probs_only_backbone`:
  - p(s_i | 백본) 형태의 조건부 확률 계산
- `--unconditional_probs_only`:
  - one-pass로 unconditional 확률 계산

## 3) 샘플링/성능 옵션

- `--backbone_noise`:
  - 백본 좌표에 추가할 가우시안 노이즈 표준편차
- `--num_seq_per_target`:
  - 타깃당 생성할 서열 개수
- `--batch_size`:
  - 추론 배치 크기
- `--max_length`:
  - 허용 최대 서열 길이
- `--sampling_temp`:
  - 샘플링 온도(문자열로 여러 값 가능, 예: `"0.1 0.2"`)
  - 낮을수록 보수적, 높을수록 다양성 증가

## 4) 입출력 경로 옵션

- `--out_folder`:
  - 결과 출력 폴더
- `--pdb_path`:
  - 단일 PDB 입력 경로
- `--pdb_path_chains`:
  - 단일 PDB에서 디자인할 체인 지정 (예: `"A B"`)
- `--jsonl_path`:
  - 파싱된 pdb jsonl 입력 경로

## 5) 체인/포지션 고정 옵션

- `--chain_id_jsonl`:
  - 어떤 체인을 디자인/고정할지 정의한 jsonl
- `--fixed_positions_jsonl`:
  - 체인별 고정 residue 위치 정의 jsonl
  - 주의: 위치 번호는 보통 체인 내부 1-based 인덱스

## 6) 아미노산 제한/바이어스 옵션

- `--omit_AAs`:
  - 전체적으로 제외할 아미노산 지정 (예: `"AC"`)
- `--bias_AA_jsonl`:
  - 전역 AA 바이어스 설정 jsonl (예: A는 덜, F는 더)
- `--bias_by_res_jsonl`:
  - residue 위치별 바이어스 설정 jsonl
- `--omit_AA_jsonl`:
  - 특정 체인/위치에서 금지할 아미노산 설정 jsonl

## 7) PSSM 관련 옵션

- `--pssm_jsonl`:
  - PSSM 입력 jsonl
- `--pssm_multi`:
  - PSSM과 MPNN 예측 혼합 비율 (`0.0`~`1.0`)
  - `0.0`: MPNN 위주, `1.0`: PSSM 위주
- `--pssm_threshold`:
  - 위치별 허용 아미노산 제한 임계값
- `--pssm_log_odds_flag`:
  - log-odds 형식 사용 여부 (`0/1`)
- `--pssm_bias_flag`:
  - PSSM을 bias로 적용할지 여부 (`0/1`)

## 8) 대칭/연동 제약 옵션

- `--tied_positions_jsonl`:
  - 여러 위치를 함께 묶어(동일/연동) 샘플링하도록 지정

## 자주 쓰는 조합 예시

### 단일 PDB, 체인 B만 디자인

```bash
python protein_mpnn_run.py \
  --pdb_path ./input.pdb \
  --pdb_path_chains "A", "B" \
  --out_folder ./outputs \
  --num_seq_per_target 8 \
  --sampling_temp "0.1 0.2" \
  --batch_size 1
```

### 체인 B 디자인 + 일부 위치 고정

```bash
python protein_mpnn_run.py \
  --jsonl_path ./parsed_pdbs.jsonl \
  --chain_id_jsonl ./assigned_pdbs.jsonl \
  --fixed_positions_jsonl ./fixed_positions.jsonl \
  --out_folder ./outputs
```

## 참고

- 원문 옵션 정의: `proteinmpnn/README.md`
- 고정 위치 json 생성 스크립트: `proteinmpnn/helper_scripts/make_fixed_positions_dict.py`
