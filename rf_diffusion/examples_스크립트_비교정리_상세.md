# RFdiffusion Examples 비교 정리 (상세)

기준 경로: `C:\project\sim_pip\RFdiffusion\examples`

## 읽는 방법
- 아래 내용은 각 `.sh`가 `config/inference/base.yaml` 기본값 대비 어떤 파라미터를 바꾸는지 정리한 문서입니다.
- 같은 계열 파일끼리 무엇이 달라지는지 빠르게 비교할 수 있게 구성했습니다.

---

## 1) Unconditional 계열

### `design_unconditional.sh`
기능:
- 조건 없이 단량체를 생성하는 가장 기본 예제.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_unconditional`
- `contigmap.contigs=[100-200]`: 길이 100~200 aa를 샘플링
- `inference.num_designs=10`

### `design_unconditional_w_contact_potential.sh`
기능:
- 기본 unconditional에 접촉(contact) 유도 potential 추가.

추가/변경 파라미터:
- `inference.output_prefix=example_outputs/design_unconditional_w_contact_potential`
- `contigmap.contigs=[100-200]`
- `inference.num_designs=10`
- `potentials.guiding_potentials=["type:monomer_contacts,weight:0.05"]`: 단량체 내 접촉 유도

### `design_unconditional_w_monomer_ROG.sh`
기능:
- 기본 unconditional에 compactness(응집도) 유도 potential 추가.

추가/변경 파라미터:
- `inference.output_prefix=example_outputs/design_monomer_ROG_unconditional`
- `contigmap.contigs=[100-200]`
- `inference.num_designs=10`
- `potentials.guiding_potentials=["type:monomer_ROG,weight:1,min_dist:5"]`: ROG 기반 compactness 유도
- `potentials.guide_scale=2`
- `potentials.guide_decay=quadratic`

---

## 2) Motif Scaffolding 계열

### `design_motifscaffolding.sh`
기능:
- 입력 PDB의 특정 모티프(A163-181)를 유지하며 주변 scaffold 생성.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_motifscaffolding`
- `inference.input_pdb=input_pdbs/5TPN.pdb`
- `contigmap.contigs=[10-40/A163-181/10-40]`: 모티프 전후 길이 샘플링
- `inference.num_designs=10`

### `design_motifscaffolding_inpaintseq.sh`
기능:
- motif scaffolding + 모티프 일부 서열 identity를 마스킹해 재설계 허용.

추가/변경 파라미터:
- `inference.output_prefix=example_outputs/design_motifscaffolding_inpaintseq`
- `inference.input_pdb=input_pdbs/5TPN.pdb`
- `contigmap.contigs=[10-40/A163-181/10-40]`
- `inference.num_designs=10`
- `contigmap.inpaint_seq=[A163-168/A170-171/A179]`: 지정 residue 서열 마스킹

### `design_motifscaffolding_with_target.sh`
기능:
- 타깃 체인을 포함한 복합체 상황에서 motif scaffolding 수행.

추가/변경 파라미터:
- `--` 실행은 `python ../scripts/run_inference.py` (동일 엔트리)
- `inference.output_prefix=example_outputs/design_motifscaffolding_with_target`
- `inference.input_pdb=input_pdbs/1YCR.pdb`
- `contigmap.contigs=[A25-109/0 0-70/B17-29/0-70]`: 타깃 체인 + chain break + 디자인 체인
- `contigmap.length=70-120`: 확산되는 체인의 총 길이 제약
- `inference.num_designs=10`
- `inference.ckpt_override_path=../models/Complex_base_ckpt.pt`: complex 특화 ckpt 사용

### `design_enzyme.sh`
기능:
- 효소 활성부위(작은 motif 다중 residue) 스캐폴딩 + substrate contact potential.

추가/변경 파라미터:
- `inference.output_prefix=example_outputs/design_enzyme`
- `inference.input_pdb=input_pdbs/5an7.pdb`
- `contigmap.contigs=[10-100/A1083-1083/10-100/A1051-1051/10-100/A1180-1180/10-100]`
- `potentials.guiding_potentials=["type:substrate_contacts,s:1,r_0:8,rep_r_0:5.0,rep_s:2,rep_r_min:1"]`
- `potentials.guide_scale=1`
- `potentials.substrate=LLK`: substrate 이름
- `inference.ckpt_override_path=../models/ActiveSite_ckpt.pt`: active-site 특화 ckpt

### `design_nickel.sh`
기능:
- 대칭 니켈 결합 motif scaffolding(C4) + oligomer contact potential.

추가/변경 파라미터:
- `inference.symmetry=C4`
- `inference.num_designs=15`
- `inference.output_prefix=example_outputs/design_nickel`
- `potentials.guiding_potentials=["type:olig_contacts,weight_intra:1,weight_inter:0.06"]`
- `potentials.olig_intra_all=True`
- `potentials.olig_inter_all=True`
- `potentials.guide_scale=2`
- `potentials.guide_decay=quadratic`
- `inference.input_pdb=input_pdbs/nickel_symmetric_motif.pdb`
- `contigmap.contigs=[50/A2-4/50/0 50/A7-9/50/0 50/A12-14/50/0 50/A17-19/50/0]`
- `inference.ckpt_override_path=$ckpt` (`$ckpt`는 스크립트에서 `../models/Base_epoch8_ckpt.pt`로 설정)

---

## 3) Partial Diffusion 계열

### `design_partialdiffusion.sh`
기능:
- 입력 구조(2KL8) 전체를 일부 timestep만 노이즈/복원하여 구조 다양화.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_partialdiffusion`
- `inference.input_pdb=input_pdbs/2KL8.pdb`
- `contigmap.contigs=[79-79]`: 전체 길이(79aa) 대응
- `inference.num_designs=10`
- `diffuser.partial_T=10`: 부분 확산 스텝

### `design_partialdiffusion_withseq.sh`
기능:
- partial diffusion + 특정 구간(예: peptide) 서열 고정.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_partialdiffusion_peptidewithsequence`
- `inference.input_pdb=input_pdbs/peptide_complex_ideal_helix.pdb`
- `contigmap.contigs=["172-172/0 34-34"]`: scaffold + peptide 체인 구성
- `diffuser.partial_T=10`
- `inference.num_designs=10`
- `contigmap.provide_seq=[172-205]`: 해당 인덱스 구간 서열 고정

### `design_partialdiffusion_multipleseq.sh`
기능:
- partial diffusion + 여러 비연속 구간 서열 고정.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_partialdiffusion_peptidewithmultiplesequence`
- `inference.input_pdb=input_pdbs/peptide_complex_ideal_helix.pdb`
- `contigmap.contigs=["172-172/0 34-34"]`
- `diffuser.partial_T=10`
- `inference.num_designs=10`
- `contigmap.provide_seq=[172-177,200-205]`: 다중 구간 서열 고정

---

## 4) PPI / Binder 계열

### `design_ppi.sh`
기능:
- 타깃 표면 hotspot을 지정해 binder를 자유형으로 생성.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_ppi`
- `inference.input_pdb=input_pdbs/insulin_target.pdb`
- `contigmap.contigs=[A1-150/0 70-100]`: 타깃 + chain break + binder 길이 샘플링
- `ppi.hotspot_res=[A59,A83,A91]`
- `inference.num_designs=10`
- `denoiser.noise_scale_ca=0`
- `denoiser.noise_scale_frame=0`

### `design_ppi_flexible_peptide.sh`
기능:
- flexible peptide 구조를 함께 inpaint하며 binder 설계.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_ppi_flexible_peptide`
- `inference.input_pdb=input_pdbs/3IOL.pdb`
- `contigmap.contigs=[B10-35/0 70-100]`
- `ppi.hotspot_res=[B28,B29]`
- `inference.num_designs=10`
- `contigmap.inpaint_str=[B10-35]`: peptide 구조 마스킹

### `design_ppi_flexible_peptide_with_secondarystructure_specification.sh`
기능:
- flexible peptide binder 설계 + peptide를 helix로 유도.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_ppi_flexible_peptide_with_secondarystructure`
- `inference.input_pdb=input_pdbs/tau_peptide.pdb`
- `contigmap.contigs=[70-100/0 B165-178]`
- `inference.num_designs=10`
- `contigmap.inpaint_str=[B165-178]`
- `scaffoldguided.scaffoldguided=True`
- `contigmap.inpaint_str_helix=[B165-178]`: 해당 구간 helix 지정

### `design_ppi_scaffolded.sh`
기능:
- binder의 coarse-grained fold를 미리 준비된 scaffold 집합으로 제한.

변경 파라미터:
- `scaffoldguided.target_path=input_pdbs/insulin_target.pdb`
- `inference.output_prefix=example_outputs/design_ppi_scaffolded`
- `scaffoldguided.scaffoldguided=True`
- `ppi.hotspot_res=[A59,A83,A91]`
- `scaffoldguided.target_pdb=True`
- `scaffoldguided.target_ss=target_folds/insulin_target_ss.pt`
- `scaffoldguided.target_adj=target_folds/insulin_target_adj.pt`
- `scaffoldguided.scaffold_dir=./ppi_scaffolds/`
- `inference.num_designs=10`
- `denoiser.noise_scale_ca=0`
- `denoiser.noise_scale_frame=0`

---

## 5) Symmetric Oligomer 계열

### `design_cyclic_oligos.sh`
기능:
- 대칭 설정 프리셋으로 C6 올리고머 생성.

변경 파라미터:
- `--config-name=symmetry`: `symmetry.yaml` 기반 실행
- `inference.symmetry=C6`
- `inference.num_designs=10`
- `inference.output_prefix=example_outputs/C6_oligo`
- `potentials.guiding_potentials=["type:olig_contacts,weight_intra:1,weight_inter:0.1"]`
- `potentials.olig_intra_all=True`
- `potentials.olig_inter_all=True`
- `potentials.guide_scale=2.0`
- `potentials.guide_decay=quadratic`
- `contigmap.contigs=[480-480]`: 총 길이 480

### `design_dihedral_oligos.sh`
기능:
- 대칭 설정 프리셋으로 D2 올리고머 생성.

변경 파라미터:
- `--config-name=symmetry`
- `inference.symmetry=D2`
- `inference.num_designs=10`
- `inference.output_prefix=example_outputs/D2_oligo`
- `potentials.guiding_potentials=["type:olig_contacts,weight_intra:1,weight_inter:0.1"]`
- `potentials.olig_intra_all=True`
- `potentials.olig_inter_all=True`
- `potentials.guide_scale=2.0`
- `potentials.guide_decay=quadratic`
- `contigmap.contigs=[320-320]`: 총 길이 320

### `design_tetrahedral_oligos.sh`
기능:
- 대칭 설정 프리셋으로 tetrahedral 올리고머 생성.

변경 파라미터:
- `--config-name=symmetry`
- `inference.symmetry=tetrahedral`
- `inference.num_designs=10`
- `inference.output_prefix=example_outputs/tetrahedral_oligo`
- `potentials.guiding_potentials=["type:olig_contacts,weight_intra:1,weight_inter:0.1"]`
- `potentials.olig_intra_all=True`
- `potentials.olig_inter_all=True`
- `potentials.guide_scale=2.0`
- `potentials.guide_decay=quadratic`
- `contigmap.contigs=[600-600]`: 총 길이 600

---

## 6) Scaffold-Guided Fold 생성

### `design_timbarrel.sh`
기능:
- TIM barrel scaffold 세트를 사용해 fold를 제한한 monomer 생성.

변경 파라미터:
- `inference.output_prefix=example_outputs/design_tim_barrel`
- `scaffoldguided.scaffoldguided=True`
- `scaffoldguided.target_pdb=False`: 타깃 없는 monomer 모드
- `scaffoldguided.scaffold_dir=tim_barrel_scaffold/`
- `inference.num_designs=10`
- `denoiser.noise_scale_ca=0.5`
- `denoiser.noise_scale_frame=0.5`
- `scaffoldguided.sampled_insertion=0-5`
- `scaffoldguided.sampled_N=0-5`
- `scaffoldguided.sampled_C=0-5`

---

## 7) Macrocyclic 계열

### `design_macrocyclic_monomer.sh`
기능:
- cyclic peptide monomer 생성.

변경 파라미터:
- `--config-name base`
- `inference.output_prefix=example_outputs/uncond_cycpep`
- `inference.num_designs=10`
- `contigmap.contigs=[12-18]`: 길이 12~18
- `inference.input_pdb=input_pdbs/7zkr_GABARAP.pdb`
- `inference.cyclic=True`
- `diffuser.T=50`
- `inference.cyc_chains='a'`

### `design_macrocyclic_binder.sh`
기능:
- cyclic peptide binder 생성(타깃 + hotspot 기반).

변경 파라미터:
- `--config-name base`
- `inference.output_prefix=example_outputs/diffused_binder_cyclic2`
- `inference.num_designs=10`
- `contigmap.contigs=[12-18 A3-117/0]`: cyclic binder 길이 + 타깃 체인 포함
- `inference.input_pdb=./input_pdbs/7zkr_GABARAP.pdb`
- `inference.cyclic=True`
- `diffuser.T=50`
- `inference.cyc_chains='a'`
- `ppi.hotspot_res=['A51','A52','A50','A48','A62','A65']`

---

## 빠른 비교 포인트 (실전)
- “기능 전환” 키: `inference.input_pdb`, `contigmap.contigs`, `diffuser.partial_T`, `inference.symmetry`, `scaffoldguided.*`, `inference.cyclic`
- “결합 유도” 키: `ppi.hotspot_res`, `potentials.guiding_potentials`
- “구조/서열 제약” 키: `contigmap.inpaint_seq`, `contigmap.inpaint_str`, `contigmap.provide_seq`, `contigmap.inpaint_str_helix`
- “모델 선택” 키: `inference.ckpt_override_path`
