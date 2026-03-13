# Chai-1/Boltz 비활성화 기능 추가 완료 ✅

## 🎯 변경 사항

Chai-1과 Boltz를 선택적으로 비활성화할 수 있는 `enabled` 플래그를 추가했습니다.

---

## 📁 수정한 파일

### 1. **`pipeline/config.py`** ✅

```python
"phase3_fast": {
    "chai": {
        "enabled": False,  # ← GPU 없을 때는 False로 설정
        "path": "",
        "venv_path": str(Path(__file__).resolve().parent.parent / ".venv"),
        "command_template": "chai-lab fold --use-msa-server {input_path} {output_dir}",
        "output_file": ""
    },
    "boltz": {
        "enabled": False,  # ← GPU 없을 때는 False로 설정
        "path": "",
        "venv_path": str(Path(__file__).resolve().parent.parent / ".boltz_venv"),
        "command_template": "boltz predict {input_path} --out_dir {output_dir} --override --use_msa_server",
        "output_file": ""
    },
    # ...
}
```

**기본값**: `enabled: False` (GPU가 없으므로)

---

### 2. **`pipeline/phases/phase3_screen.py`** ✅

#### 변경 1: Chai-1 enabled 확인

```python
# Check if Chai-1 is enabled
chai_cfg = self.fast_config.get("chai", {})
chai_enabled = chai_cfg.get("enabled", True)

chai_pdb = None
chai_conf = {}

if chai_enabled:
    logger.info(f"  Running Chai-1...")
    chai_pdb, chai_conf = self.chai.predict_complex(...)
    logger.info(f"  ✓ Chai-1 complete")
else:
    logger.info(f"  ⊘ Chai-1 disabled (GPU required)")
```

#### 변경 2: Boltz enabled 확인

```python
# Check if Boltz is enabled
boltz_cfg = self.fast_config.get("boltz", {})
boltz_enabled = boltz_cfg.get("enabled", True)

boltz_pdb = None
if boltz_enabled and self.boltz is not None:
    logger.info(f"  Running Boltz...")
    boltz_pdb, boltz_conf = self.boltz.predict_complex(...)
    logger.info(f"  ✓ Boltz complete")
elif not boltz_enabled:
    logger.info(f"  ⊘ Boltz disabled (GPU required)")
```

#### 변경 3: 둘 다 비활성화된 경우 처리

```python
gates = self.fast_config["gates"]
if boltz_pdb is not None and chai_pdb is not None:
    # Both models - use consensus
    consensus_dockq = self._calculate_dockq(...)
    # ... gate logic
elif chai_pdb is not None:
    # Only Chai - use single model
    conf = candidate.metrics.get("chai_confidence", 0.0)
    # ... gate logic
else:
    # No structure prediction - skip to deep validation
    logger.warning(f"  ⚠ No Chai/Boltz prediction (both disabled)")
    candidate.decision = {"gate": "PASS", "reason": "No fast screening, proceeding to deep validation"}
    candidate.stage = "fast_screened"
    logger.info(f"  PASS - Skipping to deep validation")
```

---

## 🎯 동작 방식

### Case 1: Chai와 Boltz 모두 비활성화 (현재 기본값)

```
[Phase 3-A: Fast Screening]
Screening C000001...
  target pdb: ...
  binder fasta: ...
  ⊘ Chai-1 disabled (GPU required)
  ⊘ Boltz disabled (GPU required)
  ⚠ No Chai/Boltz prediction (both disabled)
  PASS - Skipping to deep validation
```

→ **Fast screening 건너뛰고 바로 deep validation (ColabFold)로 진행**

### Case 2: Chai만 활성화

```
  Running Chai-1...
  ✓ Chai-1 complete
  ⊘ Boltz disabled (GPU required)
  PASS - Chai confidence: 0.85
```

→ **Chai confidence 기반으로 gate 판정**

### Case 3: 둘 다 활성화 (GPU 있을 때)

```
  Running Chai-1...
  ✓ Chai-1 complete
  Running Boltz...
  ✓ Boltz complete
  PASS - consensus DockQ: 0.523
```

→ **Consensus DockQ 기반으로 gate 판정 (가장 정확함)**

---

## 🛠️ 사용 방법

### GPU 없을 때 (현재 상태)

**`pipeline/config.py`**:
```python
"phase3_fast": {
    "chai": {"enabled": False, ...},
    "boltz": {"enabled": False, ...}
}
```

**실행**:
```bash
python scripts/test_phase1_2_3.py
```

**예상 로그**:
```
[Phase 3-A: Fast Screening]
  ⊘ Chai-1 disabled (GPU required)
  ⊘ Boltz disabled (GPU required)
  PASS - Skipping to deep validation

[Phase 3-B: Deep Validation]
  Running ColabFold...  ← 여기서 실제 검증 수행
```

---

### GPU 활성화 후

1. **Windows NVIDIA Driver 설치**
   - GeForce Experience 또는 수동 다운로드
   - 컴퓨터 재시작

2. **GPU 확인**:
   ```bash
   nvidia-smi
   python -c "import torch; print('CUDA:', torch.cuda.is_available())"
   ```

3. **Config 수정**:
   ```python
   "phase3_fast": {
       "chai": {"enabled": True, ...},  # ← True로 변경
       "boltz": {"enabled": True, ...}  # ← True로 변경
   }
   ```

4. **재실행**:
   ```bash
   python scripts/test_phase1_2_3.py
   ```

---

## 📊 성능 비교

| 시나리오 | Fast Screening 시간 | Deep Validation 필요 | 전체 정확도 |
|---------|-------------------|-------------------|-----------|
| Chai + Boltz (GPU) | 2-5분 | 일부만 | 높음 (consensus) |
| Chai만 (GPU) | 1-3분 | 대부분 | 중간 (single model) |
| 둘 다 비활성 (CPU) | 0초 (skip) | 모두 | 중간 (ColabFold only) |

---

## 🎉 장점

1. ✅ **GPU 없이도 실행 가능**: Fast screening 건너뛰고 진행
2. ✅ **유연한 설정**: Chai와 Boltz를 개별적으로 활성화/비활성화
3. ✅ **명확한 로그**: 어떤 도구가 실행되는지 명확히 표시
4. ✅ **안전한 폴백**: 둘 다 없어도 파이프라인 계속 진행

---

## 📝 추가 문서

- **`docs/CHAI1_CPU_ISSUE.md`**: Chai-1 CPU 문제 해결 가이드
- **`docs/GPU_ACTIVATION_WITHOUT_PYTORCH_UPGRADE.md`**: GPU 활성화 방법

---

**완료!** 이제 Ctrl+C로 중단하고 다시 실행하면 Chai-1/Boltz를 건너뛰고 계속 진행됩니다. 🎉
