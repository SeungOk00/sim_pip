# RFdiffusion 바인더 설계 - 빠른 참조

## 🚀 실행 명령어 (핵심)

```bash
cd /home01/hpc194a02/test/sim_pip/RFdiffusion

python scripts/run_inference.py \
  inference.input_pdb=<타겟PDB> \
  inference.output_prefix=<출력경로> \
  inference.num_designs=10 \
  'contigmap.contigs=[<체인><시작>-<끝>/0 <바인더길이>-<바인더길이>]' \
  'ppi.hotspot_res=[<체인><잔기>,<체인><잔기>,...]' \
  diffuser.T=50 \
  denoiser.noise_scale_ca=0 \
  denoiser.noise_scale_frame=0
```

## 📋 실전 예시

### 인슐린 수용체 바인더
```bash
python scripts/run_inference.py \
  inference.input_pdb=input_pdbs/insulin_receptor.pdb \
  inference.output_prefix=outputs/insulin_binder \
  inference.num_designs=10 \
  'contigmap.contigs=[A1-150/0 70-100]' \
  'ppi.hotspot_res=[A59,A83,A91]' \
  diffuser.T=50 \
  denoiser.noise_scale_ca=0 \
  denoiser.noise_scale_frame=0
```

## 🔧 주요 파라미터

| 파라미터 | 값 | 설명 |
|---------|---|------|
| `inference.input_pdb` | 파일경로 | 타겟 PDB |
| `inference.num_designs` | 10-10000 | 생성할 디자인 수 |
| `contigmap.contigs` | `[A1-150/0 70-100]` | 타겟+바인더 정의 |
| `ppi.hotspot_res` | `[A30,A33,A34]` | 핫스팟 잔기 (3-6개) |
| `diffuser.T` | 50 | 디퓨전 스텝 |
| `denoiser.noise_scale_ca` | 0.0 | 노이즈 (0=고품질) |

## 📝 파이프라인 설정 (configs/run.yaml)

```yaml
phase2:
  rfdiffusion:
    path: /home01/hpc194a02/test/sim_pip/RFdiffusion
    de_novo_T: 50              # 디퓨전 스텝
    binder_length: "70-100"    # 바인더 길이
    noise_scale: 0.0           # 노이즈 스케일
    num_designs: 10            # 디자인 수
```

## ⚙️ 파이프라인에서 사용되는 함수

```python
# pipeline/utils/tool_wrapper.py
rfdiffusion = RFdiffusionRunner(tool_path, dry_run=False)

backbones = rfdiffusion.generate_binder(
    target_pdb=Path("target.pdb"),
    target_chain="A",
    target_residues="1-150",
    hotspot_residues=[30, 33, 34, 45, 67, 89],
    binder_length="70-100",
    output_dir=Path("outputs/"),
    num_designs=10,
    T=50,
    noise_scale=0.0
)
```

## 📊 출력

```
outputs/
├── design_0.pdb      # 생성된 구조 (폴리글리신 백본)
├── design_0.trb      # 메타데이터
├── design_1.pdb
├── design_1.trb
└── ...
```

## ⚠️ 체크리스트

- [ ] conda 환경 활성화: `conda activate SE3nv`
- [ ] GPU 사용 가능 확인: `nvidia-smi`
- [ ] 타겟 PDB 파일 준비 (크롭 완료)
- [ ] 핫스팟 잔기 3-6개 선택
- [ ] Contig 문자열 작은따옴표로 감싸기
- [ ] Pilot 실행 (num_designs=5) 먼저 테스트

## 📚 더 자세한 정보

- 전체 가이드: `docs/RFDIFFUSION_GUIDE.md`
- RFdiffusion README: `RFdiffusion/README.md`
- 예제 스크립트: `RFdiffusion/examples/design_ppi.sh`
