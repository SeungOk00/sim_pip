# Phase3 Tool Options (Chai-1 / Boltz) 상세 정리

이 문서는 `C:\project\sim_pip` 로컬 소스 기준으로, Phase3에서 쓰는 두 툴의 CLI 옵션을 정리합니다.

- Chai-1 기준 소스: `chai-1/chai_lab/main.py`, `chai-1/chai_lab/chai1.py`
- Boltz 기준 소스: `boltz/src/boltz/main.py`

## 1) Chai-1 (`chai-lab fold`)

기본 실행형:

```bash
chai-lab fold [OPTIONS] <fasta_file> <output_dir>
```

- `<fasta_file>`: 복합체 입력 FASTA
- `<output_dir>`: 출력 디렉터리 (비어 있어야 함)

### 옵션 상세

| 옵션(개념) | 기본값 | 설명 | 언제 조정?
|---|---:|---|---|
| `--use-esm-embeddings/--no-use-esm-embeddings` | `True` | ESM 임베딩 사용 여부 | 속도/메모리 제약 시 비활성화 검토 |
| `--use-msa-server` | `False` | MSA 서버(기본 ColabFold) 자동 생성 사용 | 입력에 MSA가 없을 때 필수 |
| `--msa-server-url` | `https://api.colabfold.com` | MSA 서버 주소 | 사내/커스텀 MSA 서버 사용 시 |
| `--msa-directory` | `None` | 사전 계산된 MSA 디렉터리 경로 | 외부에서 준비한 MSA 재사용 시 |
| `--constraint-path` | `None` | restraint 파일 경로 | 포켓/거리 제약 반영 시 |
| `--use-templates-server` | `False` | 템플릿 서버 사용 | 템플릿 기반 성능 향상 기대 시 |
| `--template-hits-path` | `None` | 템플릿 hits 파일 경로 | 사전 계산 템플릿을 쓸 때 |
| `--recycle-msa-subsample` | `0` | recycle 단계 MSA sub-sample 크기 | 메모리 최적화/실험 시 |
| `--num-trunk-recycles` | `3` | trunk recycle 횟수 | 품질 vs 속도 trade-off |
| `--num-diffn-timesteps` | `200` | diffusion timestep 수 | 샘플링 품질/시간 조정 |
| `--num-diffn-samples` | `5` | diffusion 샘플 수 | 다양성 증가 목적 |
| `--num-trunk-samples` | `1` | trunk 샘플 수 | 다양성 확장 실험 시 |
| `--seed` | `None` | 랜덤 시드 | 재현성 필요 시 고정 |
| `--device` | `None` (`cuda:0` 사용) | 실행 장치 지정 | 멀티GPU/CPU 강제 시 |
| `--low-memory/--no-low-memory` | `True` | 메모리 절약 모드 | 메모리 충분하면 비활성화 실험 |
| `--fasta-names-as-cif-chains` | `False` | FASTA entity 이름을 CIF chain 이름으로 사용 | chain 명시적 제어 필요 시 |

추가 서브커맨드:

- `chai-lab a3m-to-pqt <directory> [output_directory]`
  - `.a3m`들을 합쳐 `aligned.pqt` 생성
- `chai-lab citation`

---

## 2) Boltz (`boltz predict`)

기본 실행형:

```bash
boltz predict <data> [OPTIONS]
```

- `<data>`: `.fasta` 또는 `.yaml` 파일/디렉터리

### 옵션 상세

| 옵션 | 기본값 | 설명 | 언제 조정?
|---|---:|---|---|
| `--out_dir PATH` | `./` | 출력 루트 디렉터리 | 파이프라인 결과 분리 시 |
| `--cache PATH` | `~/.boltz` (또는 `$BOLTZ_CACHE`) | 모델/데이터 캐시 위치 | 공용 캐시 사용 시 |
| `--checkpoint PATH` | `None` | 구조 예측 모델 체크포인트 | 커스텀 ckpt 사용 시 |
| `--affinity_checkpoint PATH` | `None` | affinity 체크포인트 | 커스텀 affinity 모델 시 |
| `--devices INT` | `1` | 사용 디바이스 수 | 멀티 GPU 추론 |
| `--accelerator [gpu/cpu/tpu]` | `gpu` | 가속기 종류 | CPU fallback 시 |
| `--recycling_steps INT` | `3` | recycle 횟수 | 품질/시간 조정 |
| `--sampling_steps INT` | `200` | diffusion sampling step | 품질/시간 조정 |
| `--diffusion_samples INT` | `1` | diffusion 샘플 수 | 다양성 증가 |
| `--max_parallel_samples INT` | `5` | 병렬 샘플 상한 | VRAM 맞춰 조정 |
| `--step_scale FLOAT` | `None` (모델별 내부 기본 사용) | diffusion step 크기 | 다양성/안정성 조정 |
| `--write_full_pae` | `False` | full PAE npz 저장 | 분석용 상세 출력 필요 시 |
| `--write_full_pde` | `False` | full PDE npz 저장 | 분석용 상세 출력 필요 시 |
| `--output_format [pdb/mmcif]` | `mmcif` | 구조 출력 포맷 | downstream 도구 호환 |
| `--num_workers INT` | `2` | dataloader worker 수 | CPU 자원 최적화 |
| `--override` | `False` | 기존 결과 덮어쓰기 | 재실행 시 |
| `--seed INT` | `None` | 랜덤 시드 | 재현성 |
| `--use_msa_server` | `False` | MSA 서버 자동 생성 | MSA 미제공 입력 처리 |
| `--msa_server_url STR` | `https://api.colabfold.com` | MSA 서버 URL | 사내 서버 사용 |
| `--msa_pairing_strategy STR` | `greedy` | 멀티체인 pairing 전략 | 페어링 전략 실험 |
| `--msa_server_username STR` | `None` | MSA 서버 basic auth ID | 인증 서버 |
| `--msa_server_password STR` | `None` | MSA 서버 basic auth PW | 인증 서버 |
| `--api_key_header STR` | `None` | API 키 헤더 이름 | API 키 방식 인증 |
| `--api_key_value STR` | `None` | API 키 값 | API 키 방식 인증 |
| `--use_potentials` | `False` | steering potentials 사용 | 유도형 샘플링 실험 |
| `--model [boltz1/boltz2]` | `boltz2` | 사용할 모델 선택 | 성능/자원에 맞춤 |
| `--method STR` | `None` | method conditioning 값 | Boltz2 method 조건 실험 |
| `--preprocessing-threads INT` | `CPU 코어수` | 전처리 병렬 스레드 | 전처리 속도 개선 |
| `--affinity_mw_correction` | `False` | affinity MW 보정 적용 | affinity head 실험 |
| `--sampling_steps_affinity INT` | `200` | affinity 샘플링 step | affinity 정확도/시간 조정 |
| `--diffusion_samples_affinity INT` | `5` | affinity diffusion 샘플 수 | affinity 안정화 |
| `--max_msa_seqs INT` | `8192` | MSA 최대 시퀀스 수 | 메모리/속도 제어 |
| `--subsample_msa` | `False`(flag 미지정 시) | MSA subsample 활성화 | 대형 MSA 절감 |
| `--num_subsampled_msa INT` | `1024` | subsample 개수 | subsample 강도 조정 |
| `--no_kernels` | `False` | 커스텀 커널 비활성화 | 호환성 이슈 회피 |
| `--write_embeddings` | `False` | 임베딩(s,z) 저장 | 후처리/분석용 |

---

## 3) 파이프라인 반영 시 실무 권장값 (현재 워크플로우 기준)

### Chai-1

- 권장 시작점:
  - `--use-msa-server`
  - `--use-templates-server`
  - 필요시 `--seed` 고정
- 대량 스크리닝 속도 우선:
  - `num_diffn_samples`를 줄이고 후보 수를 늘리는 방식 권장

### Boltz

- 권장 시작점:
  - `--model boltz2`
  - `--use_msa_server`
  - `--override` (같은 폴더 재실행 시)
- VRAM 부족 시:
  - `--diffusion_samples` 축소
  - `--max_parallel_samples` 축소
  - 필요하면 `--sampling_steps` 축소

---

## 4) 주의사항

- Chai-1: `output_dir`는 비어 있어야 함(코드상 non-empty 체크).
- Boltz: `--use_msa_server` 미사용 시 입력에 MSA 정보가 필요할 수 있음.
- Boltz 인증: basic auth(`--msa_server_username/password`)와 API key(`--api_key_header/value`)는 동시에 쓰지 않음.

