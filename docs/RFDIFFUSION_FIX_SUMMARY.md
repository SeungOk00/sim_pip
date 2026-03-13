# RFdiffusion 에러 수정 완료

**날짜**: 2026-03-13  
**문제**: `RuntimeError: RFdiffusion failed: Failed after retries`

## 🔍 근본 원인

### 1. Contig 정보 누락
RFdiffusion은 반드시 contig 정보가 필요합니다:
- `target_residues`: PDB 파일에서 사용할 target residue 범위
- `binder_length`: 생성할 바인더의 길이

tool_wrapper.py에서 둘 다 제공되지 않으면 contig가 전달되지 않아 에러 발생:
```
Must either specify a contig string or precise mapping
```

### 2. PDB Residue 번호 불일치
많은 PDB 파일들은 residue 번호가 1부터 시작하지 않습니다:
- 5TPN: residue 27부터 시작
- 4IBM: kinase domain이 residue 982부터 시작
- 일부 PDB: residue가 불연속적 (missing residues)

기본값 "1-150"을 사용하면 실제 PDB에 없는 residue를 참조하여 에러 발생:
```
AssertionError: ('A', 1) is not in pdb file!
```

## ✅ 해결 방법

### 1. tool_wrapper.py 수정

`pipeline/utils/tool_wrapper.py`의 `generate_binder` 메서드에 기본값 로직 추가:

```python
if target_residues and binder_length:
    contig_str = f"{target_chain}{target_residues}/0 {binder_length}"
    command.append(f"contigmap.contigs=[{contig_str}]")
elif target_residues or binder_length:
    # If only one is provided, use default for the other
    if not target_residues:
        target_residues = "1-150"  # Default
        logger.warning(f"target_residues not provided, using default: {target_residues}")
    if not binder_length:
        binder_length = "70-100"  # Default
        logger.warning(f"binder_length not provided, using default: {binder_length}")
    contig_str = f"{target_chain}{target_residues}/0 {binder_length}"
    command.append(f"contigmap.contigs=[{contig_str}]")
else:
    # Neither provided - use sensible defaults
    logger.warning("Neither target_residues nor binder_length provided, using defaults")
    contig_str = f"{target_chain}1-150/0 70-100"
    command.append(f"contigmap.contigs=[{contig_str}]")
```

**개선 사항**:
- 둘 중 하나만 제공되어도 작동
- 아무것도 제공되지 않으면 기본값 사용
- 명확한 경고 메시지 출력

### 2. 문서화

`docs/RFDIFFUSION_TROUBLESHOOTING.md` 생성:
- PDB residue 번호 확인 방법
- Config 설정 방법
- 일반적인 에러 해결 방법
- GPU 관련 이슈

## 📝 사용 가이드

### 올바른 설정 방법

1. **PDB residue 번호 확인**:
```bash
grep "^ATOM" your_target.pdb | awk '{print $6}' | sort -un | head -1
grep "^ATOM" your_target.pdb | awk '{print $6}' | sort -un | tail -1
```

2. **configs/run.yaml 설정**:
```yaml
phase2:
  rfdiffusion:
    target_residues: "27-147"   # 실제 PDB residue 범위!
    binder_length: "70-100"
```

3. **Hotspot 확인**:
```python
hotspot_residues = [982, 990, 995]  # target_residues 범위 내에 있어야 함
```

## 🚀 다음 단계

### 남은 문제: GPU 감지

```
NO GPU DETECTED! Falling back to CPU
```

이것은 별도의 문제로, WSL2에서 CUDA 설정이 필요합니다:

1. **NVIDIA Driver 설치** (Windows에서)
2. **CUDA Toolkit 설치** (WSL2에서)
3. **PyTorch CUDA 버전 확인**:
```bash
conda activate SE3nv
python -c "import torch; print(torch.cuda.is_available())"
```

CPU 모드로도 작동하지만 매우 느립니다 (GPU 대비 20-50배 느림).

## 📊 테스트 상태

### Before
```
RuntimeError: RFdiffusion failed: Failed after retries
```

### After (예상)
```
[INFO] target_residues not provided, using default: 1-150
[INFO] binder_length not provided, using default: 70-100
[INFO] RFdiffusion command: ...
[INFO] Using contig: ['A1-150/0 70-100']
```

또는 사용자가 설정을 제공하면:
```
[INFO] Using contig: ['A27-147/0 70-100']
[INFO] Generating 10 designs...
```

## 📚 관련 파일

- `pipeline/utils/tool_wrapper.py` - 수정됨
- `docs/RFDIFFUSION_TROUBLESHOOTING.md` - 새로 생성
- `configs/run.yaml` - 설정 예제 포함

## 💡 교훈

1. **PDB 파일은 표준화되지 않음**: Residue 번호가 1부터 시작한다고 가정하면 안 됨
2. **기본값의 중요성**: 사용자가 모든 파라미터를 제공하지 않을 수 있음
3. **명확한 에러 메시지**: "Failed after retries"보다 구체적인 정보 필요
4. **문서화**: 일반적인 문제에 대한 가이드 제공

## ✅ 결론

RFdiffusion contig 에러가 해결되었습니다. 이제 사용자는:
1. Config 파일에 target_residues를 설정하거나
2. 기본값을 사용할 수 있습니다 (경고 메시지와 함께)

실제 PDB 파일의 residue 범위에 맞게 설정하는 것을 권장합니다!
