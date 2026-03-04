#!/bin/bash
# RFdiffusion 실행 스크립트

RFDIFFUSION_DIR="/home01/hpc194a02/test/sim_pip/RFdiffusion"

# Conda 환경 활성화 (경로는 환경에 맞게 수정)
# source ~/miniconda3/etc/profile.d/conda.sh  # 필요시 주석 해제
# conda activate SE3nv

cd /home01/hpc194a02/test/sim_pip/test_rfdiffusion

echo "=========================================="
echo "RFdiffusion 실행"
echo "=========================================="
echo ""
echo "타겟: target.pdb"
echo "바인더: 80aa"
echo "핫스팟: A982,A990,A995"
echo "디자인 수: 2개 (테스트)"
echo ""

python $RFDIFFUSION_DIR/scripts/run_inference.py \
    inference.input_pdb=target.pdb \
    inference.output_prefix=outputs/binder \
    inference.num_designs=2 \
    'contigmap.contigs=[A982-999/0 80-80]' \
    'ppi.hotspot_res=[A982,A990,A995]' \
    diffuser.T=50 \
    denoiser.noise_scale_ca=0 \
    denoiser.noise_scale_frame=0

echo ""
echo "=========================================="
echo "실행 완료!"
echo "=========================================="
echo ""
echo "생성된 파일:"
ls -lh outputs/
