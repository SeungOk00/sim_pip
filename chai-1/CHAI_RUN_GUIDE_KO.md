# Chai-1 실행 방법 정리 (로컬 repo 기준)

이 문서는 `C:/project/sim_pip/chai-1` 내부 문서(`README.md`, `pyproject.toml`)를 기준으로 작성했습니다.

## 핵심 실행 명령

`pyproject.toml`의 CLI 엔트리포인트:

`chai-lab = "chai_lab.main:cli"`

복합체 예측 기본 명령:

```bash
chai-lab fold input.fasta output_folder
```

MSA/Template 서버 사용:

```bash
chai-lab fold --use-msa-server --use-templates-server input.fasta output_folder
```

## 입력 포맷

Chai는 복합체 전체를 담은 FASTA를 받습니다.

예시:

```text
>protein|name=target
SEQUENCE_OF_TARGET
>protein|name=binder
SEQUENCE_OF_BINDER
```

## 출력 포맷

`output_folder` 아래에 일반적으로 아래 파일이 생성됩니다.

- `pred.model_idx_0.cif` (샘플별 구조 파일)
- `scores.model_idx_0.npz` (샘플별 점수)

즉 고정 `predicted_complex.pdb`가 아니라 `pred.model_idx_*.cif` 탐색이 필요합니다.

## Pipeline 반영 원칙

Phase3에서 Chai 실행 시:

1. 타깃+바인더 FASTA 생성
2. `chai-lab fold {input_path} {output_dir} ...` 실행
3. `pred.model_idx_*.cif`를 우선 결과 구조로 사용

## 참고 파일

- `C:/project/sim_pip/chai-1/README.md`
- `C:/project/sim_pip/chai-1/pyproject.toml`
