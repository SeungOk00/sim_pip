# 출력 디렉토리 구조 최종 변경 ✅

## 🎯 최종 구조

날짜 폴더를 유지하면서 그 아래에 순차적으로 증가하는 run_id 사용:

```
data/outputs/tool/YYYY-MM-DD/run_XXX/...
```

### 예시
```
data/
├── inputs/
│   └── pdb/
│       └── 2026-03-13/
│           ├── run_001/
│           │   └── target.pdb
│           └── run_002/
│               └── target.pdb
└── outputs/
    ├── rfdiffusion/
    │   └── 2026-03-13/
    │       ├── run_001/
    │       │   ├── denovo/
    │       │   └── refinement/
    │       └── run_002/
    │           ├── denovo/
    │           └── refinement/
    ├── proteinmpnn/
    │   └── 2026-03-13/
    │       ├── run_001/
    │       │   └── mpnn/
    │       └── run_002/
    │           └── mpnn/
    ├── chai1/
    │   └── 2026-03-13/
    │       └── run_001/
    │           └── 02-19-36-024726/
    └── phase3_fast/
        └── 2026-03-13/
            ├── run_001/
            └── run_002/
```

---

## 🔄 Run ID 생성 로직

### `pipeline/utils/file_ops.py`

**새로운 함수**:

```python
def get_run_id(outputs_root: Optional[Path] = None) -> str:
    """
    Generate sequential run ID for today's date (run_001, run_002, ...)
    
    Checks all existing run directories for today across multiple tools
    and returns the next sequential number.
    """
    if outputs_root is None:
        return "run_001"
    
    date_dir = datetime.now().strftime("%Y-%m-%d")
    
    # Check multiple tool directories
    tool_dirs = [
        "rfdiffusion", "proteinmpnn", "phase3_fast", "colabfold", 
        "chai1", "boltz", "rosetta", "lab"
    ]
    
    existing_runs = []
    for tool in tool_dirs:
        tool_path = outputs_root / tool / date_dir
        if tool_path.exists():
            for item in tool_path.iterdir():
                if item.is_dir() and item.name.startswith("run_"):
                    try:
                        num = int(item.name.split("_")[1])
                        existing_runs.append(num)
                    except (ValueError, IndexError):
                        continue
    
    if not existing_runs:
        return "run_001"
    
    max_run = max(existing_runs)
    return f"run_{max_run + 1:03d}"


def get_date_dir() -> str:
    """Get current date directory (YYYY-MM-DD)"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")
```

---

## 📁 수정한 파일 (8개)

### 1. **`pipeline/utils/file_ops.py`** ✅
- `get_run_id()` 함수 수정: 순차적 run_id 생성
- `get_date_dir()` 함수 추가: 날짜 디렉토리 생성

### 2. **`main.py`** ✅
```python
# Before
run_id = get_run_id()

# After
outputs_root = project_root / config.get('paths.outputs')
run_id = get_run_id(outputs_root)
```

### 3. **`pipeline/phases/phase1_target.py`** ✅
```python
# Format: inputs/pdb/date/run_id/
date_dir = get_date_dir()
inputs_pdb_dir = ... / inputs_pdb / date_dir / state.run_id
```

### 4. **`pipeline/phases/phase2_generate.py`** ✅
```python
# Format: outputs/tool/date/run_id/
date_dir = get_date_dir()
rfdiffusion_out_dir = outputs_root / "rfdiffusion" / date_dir / state.run_id
proteinmpnn_out_dir = outputs_root / "proteinmpnn" / date_dir / state.run_id
```

### 5. **`pipeline/phases/phase3_screen.py`** ✅
```python
# Format: outputs/tool/date/run_id/
date_dir = get_date_dir()
fast_dir = outputs_root / "phase3_fast" / date_dir / state.run_id
deep_dir = outputs_root / "colabfold" / date_dir / state.run_id / "phase3_deep"
chai_output_dir = outputs_root / "chai1" / date_dir / state.run_id / unique_id / candidate_id
boltz_output_dir = outputs_root / "boltz" / date_dir / state.run_id / unique_id / candidate_id
```

**파일 검색 로직**:
```python
# Search pattern: tool/*/run_*/...
matches = sorted(outputs_root.glob(f"rfdiffusion/*/run_*/denovo/binder_{idx}.pdb"))
matches = sorted(outputs_root.glob(f"proteinmpnn/*/run_*/mpnn/backbone_{idx:03d}/seqs/*.fa"))
```

### 6. **`pipeline/phases/phase4_optimize.py`** ✅
```python
date_dir = get_date_dir()
run_dir = outputs_root / "rosetta" / date_dir / state.run_id / "phase4_opt"
```

### 7. **`pipeline/phases/phase5_lab.py`** ✅
```python
date_dir = get_date_dir()
run_dir = outputs_root / "lab" / date_dir / state.run_id / "phase5_lab"
```

### 8. **`scripts/test_phase1_2_3.py`** ✅
```python
from pipeline.utils.file_ops import get_run_id
outputs_root = project_root / "data" / "outputs"
run_id = get_run_id(outputs_root)
```

---

## 🎯 Run ID 예시

### 첫 번째 실행 (오늘)
```python
run_id = get_run_id(outputs_root)
# → "run_001"
```

**디렉토리**:
```
data/outputs/rfdiffusion/2026-03-13/run_001/
data/outputs/proteinmpnn/2026-03-13/run_001/
```

### 두 번째 실행 (같은 날)
```python
run_id = get_run_id(outputs_root)
# → "run_002"
```

**디렉토리**:
```
data/outputs/rfdiffusion/2026-03-13/run_002/
data/outputs/proteinmpnn/2026-03-13/run_002/
```

### 다음 날 첫 실행
```python
run_id = get_run_id(outputs_root)
# → "run_001"  (새로운 날짜이므로 다시 1부터)
```

**디렉토리**:
```
data/outputs/rfdiffusion/2026-03-14/run_001/
data/outputs/proteinmpnn/2026-03-14/run_001/
```

---

## ✅ 장점

1. **날짜별 그룹화**: 같은 날 실행한 run들을 쉽게 찾을 수 있음
2. **순차적 번호**: 실행 순서를 명확하게 알 수 있음
3. **짧은 ID**: `run_001`, `run_002` 등 간결한 이름
4. **매일 리셋**: 날짜가 바뀌면 다시 001부터 시작
5. **충돌 방지**: 모든 도구 디렉토리를 확인하여 중복 방지

---

## 🧪 테스트

```bash
source .venv/bin/activate

# 첫 번째 실행
python scripts/test_phase1_2_3.py
# → run_001 생성

# 두 번째 실행
python scripts/test_phase1_2_3.py
# → run_002 생성

# 확인
ls -la data/outputs/rfdiffusion/2026-03-13/
# run_001/
# run_002/
```

---

## 📊 경로 비교

| 항목 | 이전 (시간 기반) | 중간 (run_id만) | 최종 (날짜 + run_id) |
|------|-----------------|----------------|---------------------|
| 구조 | `tool/YYYY-MM-DD/HH-MM-SS/` | `tool/run_id/` | `tool/YYYY-MM-DD/run_XXX/` |
| 예시 | `rfdiffusion/2026-03-13/02-12-18/` | `rfdiffusion/2026-03-13_021218/` | `rfdiffusion/2026-03-13/run_001/` |
| 날짜 그룹화 | ✅ | ❌ | ✅ |
| 간결한 ID | ❌ | ⚠️ | ✅ |
| 순차 번호 | ❌ | ❌ | ✅ |
| 검색 용이 | ⚠️ | ✅ | ✅ |

---

**완료!** 이제 날짜별로 그룹화되고 순차적으로 증가하는 run_id를 사용합니다. 🎉
