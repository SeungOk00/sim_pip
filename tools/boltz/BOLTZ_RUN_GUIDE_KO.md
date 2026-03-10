# Boltz 실행 방법 정리 (로컬 repo 기준)

이 문서는 `C:/project/sim_pip/boltz` 내부 문서(`README.md`, `docs/prediction.md`, `pyproject.toml`)를 기준으로 작성했습니다.

## 핵심 실행 명령

Boltz CLI 엔트리포인트는 `pyproject.toml`에 아래처럼 정의되어 있습니다.

`boltz = "boltz.main:cli"`

예측 기본 명령:

```bash
boltz predict <INPUT_PATH>
```

권장(재실행/출력 지정):

```bash
boltz predict <INPUT_PATH> --out_dir <OUT_DIR> --override
```

MSA 서버 사용 시:

```bash
boltz predict <INPUT_PATH> --out_dir <OUT_DIR> --override --use_msa_server
```

## INPUT_PATH 포맷

`<INPUT_PATH>`는 다음 중 하나:

1. 단일 `.yaml` 또는 `.fasta` 파일
2. `.yaml`/`.fasta` 파일들이 있는 디렉터리

문서상 YAML이 권장되고 FASTA는 deprecated입니다.

## 출력 구조 (문서 기준)

`--out_dir` 아래에 기본적으로 다음과 같은 구조가 생깁니다.

```text
<OUT_DIR>/
  predictions/
    <input_stem>/
      <input_stem>_model_0.cif
      confidence_<input_stem>_model_0.json
      ...
```

즉 단일 고정 파일(`predicted_complex.pdb`)이 아니라, 보통 `predictions/<입력명>/...model_0.cif` 형태를 찾아야 합니다.

## Pipeline 반영 원칙

Phase3에서 Boltz 실행 시:

1. `input_path`(Boltz 입력 파일) 생성
2. `boltz predict {input_path} --out_dir {output_dir} ...` 실행
3. `output_dir/predictions/**` 아래에서 모델 구조 파일(`*.cif` 우선, 없으면 `*.pdb`) 탐색

## 참고 파일

- `C:/project/sim_pip/boltz/README.md`
- `C:/project/sim_pip/boltz/docs/prediction.md`
- `C:/project/sim_pip/boltz/pyproject.toml`
