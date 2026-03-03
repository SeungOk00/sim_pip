#!/bin/bash
# RFdiffusion 최소 테스트 - 실제 실행 명령어

echo "=========================================="
echo "RFdiffusion 실행 테스트"
echo "=========================================="
echo ""

# 1. 테스트 디렉토리 생성
TEST_DIR="/home01/hpc194a02/test/sim_pip/test_rfdiffusion"
mkdir -p $TEST_DIR/outputs
cd $TEST_DIR

echo "작업 디렉토리: $TEST_DIR"
echo ""

# 2. 테스트 타겟 다운로드
if [ ! -f "target.pdb" ]; then
    echo "테스트 타겟 다운로드 중..."
    wget -q https://files.rcsb.org/download/4IBM.pdb -O target.pdb
    if [ $? -eq 0 ]; then
        echo "✓ 다운로드 완료: target.pdb (인슐린 수용체)"
    else
        echo "✗ 다운로드 실패"
        exit 1
    fi
fi
echo ""

# 3. RFdiffusion 실행 명령어 생성
cat > run_rfdiffusion_test.sh << 'EOF'
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
echo "핫스팟: A59, A83, A91"
echo "디자인 수: 2개 (테스트)"
echo ""

python $RFDIFFUSION_DIR/scripts/run_inference.py \
  inference.input_pdb=target.pdb \
  inference.output_prefix=outputs/binder \
  inference.num_designs=2 \
  'contigmap.contigs=[A1-150/0 80-80]' \
  'ppi.hotspot_res=[A59,A83,A91]' \
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
EOF

chmod +x run_rfdiffusion_test.sh

echo "=========================================="
echo "준비 완료!"
echo "=========================================="
echo ""
echo "다음 명령어로 실행하세요:"
echo ""
echo "cd $TEST_DIR"
echo "./run_rfdiffusion_test.sh"
echo ""
echo "또는 직접:"
echo ""
echo "python /home01/hpc194a02/test/sim_pip/RFdiffusion/scripts/run_inference.py \\"
echo "  inference.input_pdb=$TEST_DIR/target.pdb \\"
echo "  inference.output_prefix=$TEST_DIR/outputs/binder \\"
echo "  inference.num_designs=1 \\"
echo "  'contigmap.contigs=[A1-150/0 80-80]' \\"
echo "  'ppi.hotspot_res=[A59,A83,A91]'"
echo ""
