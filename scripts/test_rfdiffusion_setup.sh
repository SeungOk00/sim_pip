#!/bin/bash
# RFdiffusion 단독 테스트 스크립트

echo "=========================================="
echo "RFdiffusion 단독 실행 테스트"
echo "=========================================="
echo ""

# 경로 설정
RFDIFFUSION_PATH="/home01/hpc194a02/test/sim_pip/RFdiffusion"
TEST_DIR="/home01/hpc194a02/test/sim_pip/test_rfdiffusion"

# 테스트 디렉토리 생성
mkdir -p $TEST_DIR
cd $TEST_DIR

echo "1. 환경 확인..."
echo "   RFdiffusion 경로: $RFDIFFUSION_PATH"
echo ""

# Conda 환경 확인
echo "2. Conda 환경 확인..."
if conda env list | grep -q "SE3nv"; then
    echo "   ✓ SE3nv 환경 발견"
else
    echo "   ✗ SE3nv 환경 없음 - 설치 필요"
    exit 1
fi
echo ""

# GPU 확인
echo "3. GPU 확인..."
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
    echo "   ✓ GPU 사용 가능"
else
    echo "   ⚠ nvidia-smi 없음 - CPU로 실행됨 (매우 느림)"
fi
echo ""

# 테스트 PDB 다운로드
echo "4. 테스트 타겟 다운로드..."
if [ ! -f "insulin_receptor.pdb" ]; then
    echo "   인슐린 수용체 다운로드 중..."
    wget -q https://files.rcsb.org/download/4IBM.pdb -O insulin_receptor.pdb
    if [ $? -eq 0 ]; then
        echo "   ✓ 다운로드 완료: insulin_receptor.pdb"
    else
        echo "   ✗ 다운로드 실패"
        exit 1
    fi
else
    echo "   ✓ insulin_receptor.pdb 이미 존재"
fi
echo ""

# RFdiffusion 모델 가중치 확인
echo "5. 모델 가중치 확인..."
if [ -f "$RFDIFFUSION_PATH/models/Complex_base_ckpt.pt" ]; then
    echo "   ✓ Complex_base_ckpt.pt 존재"
else
    echo "   ✗ 모델 가중치 없음"
    echo "   다음 명령어로 다운로드:"
    echo "   cd $RFDIFFUSION_PATH && bash scripts/download_models.sh"
    exit 1
fi
echo ""

echo "=========================================="
echo "테스트 실행 준비 완료!"
echo "=========================================="
echo ""
echo "다음 명령어로 RFdiffusion 실행:"
echo ""
echo "conda activate SE3nv"
echo "cd $TEST_DIR"
echo ""
echo "# 간단한 테스트 (1개 디자인)"
echo "python $RFDIFFUSION_PATH/scripts/run_inference.py \\"
echo "  inference.input_pdb=insulin_receptor.pdb \\"
echo "  inference.output_prefix=test_output/binder \\"
echo "  inference.num_designs=1 \\"
echo "  'contigmap.contigs=[A1-150/0 80-80]' \\"
echo "  'ppi.hotspot_res=[A59,A83,A91]' \\"
echo "  diffuser.T=50 \\"
echo "  denoiser.noise_scale_ca=0 \\"
echo "  denoiser.noise_scale_frame=0"
echo ""
