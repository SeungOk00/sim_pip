# 출력 디렉토리 구조 변경 완료 ✅

## 🎯 변경 사항

출력 디렉토리 구조를 **시간 기반**에서 **run_id 기반**으로 변경했습니다.

### Before (시간 기반)
```
data/outputs/tool/YYYY-MM-DD/HH-MM-SS/...
```

예시:
```
data/outputs/rfdiffusion/2026-03-13/02-12-18/denovo/
data/outputs/proteinmpnn/2026-03-13/02-12-18/mpnn/
data/outputs/chai1/2026-03-13/02-19-36-024726/C000001/
```

### After (run_id 기반)
```
data/outputs/tool/run_id/...
```

예시:
```
data/outputs/rfdiffusion/2026-03-13_021218/denovo/
data/outputs/proteinmpnn/2026-03-13_021218/mpnn/
data/outputs/chai1/2026-03-13_021936/C000001/
```

---

## 📁 수정한 파일

### 1. **`pipeline/phases/phase1_target.py`** ✅
**변경**:
```python
# Before
inputs_pdb_dir = ... / inputs_pdb / date_dir / time_dir

# After
inputs_pdb_dir = ... / inputs_pdb / state.run_id
```

**영향**: `data/inputs/pdb/run_id/`

---

### 2. **`pipeline/phases/phase2_generate.py`** ✅
**변경**:
```python
# Before
rfdiffusion_out_dir = outputs_root / "rfdiffusion" / date_dir / time_dir
proteinmpnn_out_dir = outputs_root / "proteinmpnn" / date_dir / time_dir

# After
rfdiffusion_out_dir = outputs_root / "rfdiffusion" / state.run_id
proteinmpnn_out_dir = outputs_root / "proteinmpnn" / state.run_id
```

**영향**: 
- `data/outputs/rfdiffusion/run_id/`
- `data/outputs/proteinmpnn/run_id/`

---

### 3. **`pipeline/phases/phase3_screen.py`** ✅
**변경**:
```python
# Before
fast_dir = outputs_root / "phase3_fast" / date_dir / time_dir
deep_dir = outputs_root / "colabfold" / date_dir / time_dir / "phase3_deep"
chai_output_dir = outputs_root / "chai1" / date_dir / unique_id / candidate_id
boltz_output_dir = outputs_root / "boltz" / date_dir / unique_id / candidate_id

# After
fast_dir = outputs_root / "phase3_fast" / state.run_id
deep_dir = outputs_root / "colabfold" / state.run_id / "phase3_deep"
chai_output_dir = outputs_root / "chai1" / state.run_id / unique_id / candidate_id
boltz_output_dir = outputs_root / "boltz" / state.run_id / unique_id / candidate_id
```

**파일 검색 로직도 수정**:
```python
# Before
outputs_root.glob(f"rfdiffusion/*/*/denovo/binder_{idx}.pdb")
outputs_root.glob(f"proteinmpnn/*/*/mpnn/backbone_{idx:03d}/seqs/*.fa")

# After
outputs_root.glob(f"rfdiffusion/*/denovo/binder_{idx}.pdb")
outputs_root.glob(f"proteinmpnn/*/mpnn/backbone_{idx:03d}/seqs/*.fa")
```

**영향**:
- `data/outputs/phase3_fast/run_id/`
- `data/outputs/colabfold/run_id/`
- `data/outputs/chai1/run_id/`
- `data/outputs/boltz/run_id/`

---

### 4. **`pipeline/phases/phase4_optimize.py`** ✅
**변경**:
```python
# Before
run_dir = outputs_root / "rosetta" / date_dir / time_dir / "phase4_opt"

# After
run_dir = outputs_root / "rosetta" / state.run_id / "phase4_opt"
```

**영향**: `data/outputs/rosetta/run_id/`

---

### 5. **`pipeline/phases/phase5_lab.py`** ✅
**변경**:
```python
# Before
run_dir = outputs_root / "lab" / date_dir / time_dir / "phase5_lab"

# After
run_dir = outputs_root / "lab" / state.run_id / "phase5_lab"
```

**영향**: `data/outputs/lab/run_id/`

---

## 🎯 장점

### Before (시간 기반)
- ❌ 중첩된 디렉토리 구조 (3단계)
- ❌ 파일 검색 시 와일드카드 2개 필요 (`*/*`)
- ❌ 동일 run의 파일 찾기 어려움
- ❌ 디렉토리 이름이 직관적이지 않음

### After (run_id 기반)
- ✅ 단순한 디렉토리 구조 (2단계)
- ✅ 파일 검색 시 와일드카드 1개만 필요 (`*`)
- ✅ 동일 run의 모든 출력을 쉽게 찾을 수 있음
- ✅ run_id가 명확하게 표시됨

---

## 📋 run_id 형식

**생성**: `pipeline/utils/file_ops.py`의 `get_run_id()` 함수

```python
def get_run_id() -> str:
    """Generate run ID with timestamp"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")
```

**예시**: `2026-03-13_021936`

---

## 🧪 테스트

```bash
source .venv/bin/activate
python scripts/test_phase1_2_3.py
```

**예상 출력 디렉토리**:
```
data/
├── inputs/
│   └── pdb/
│       └── 2026-03-13_021936/
│           └── target.pdb
└── outputs/
    ├── rfdiffusion/
    │   └── 2026-03-13_021936/
    │       ├── denovo/
    │       └── refinement/
    ├── proteinmpnn/
    │   └── 2026-03-13_021936/
    │       └── mpnn/
    ├── chai1/
    │   └── 2026-03-13_021936/
    │       └── 02-19-36-024726/
    ├── phase3_fast/
    │   └── 2026-03-13_021936/
    ├── colabfold/
    │   └── 2026-03-13_021936/
    ├── rosetta/
    │   └── 2026-03-13_021936/
    └── lab/
        └── 2026-03-13_021936/
```

---

## 🔄 마이그레이션

기존 데이터가 있다면 수동으로 마이그레이션:

```bash
# 예시: 기존 시간 기반 구조를 run_id 기반으로 변경
cd data/outputs/rfdiffusion
mv 2026-03-13/02-12-18 2026-03-13_021218

cd ../proteinmpnn
mv 2026-03-13/02-12-18 2026-03-13_021218

# 빈 디렉토리 제거
find data/outputs -type d -empty -delete
```

---

**완료!** 이제 모든 출력이 `run_id`로 구조화됩니다. 🎉
