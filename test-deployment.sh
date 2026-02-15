#!/bin/bash
# Pre-deployment test script for OptiMATE

echo "🧪 Testing OptiMATE before deployment..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Check Python dependencies
echo "📦 Checking Python dependencies..."
cd backend
if python -c "import gurobipy, anthropic, openai" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Python dependencies OK"
else
    echo -e "${RED}✗${NC} Missing Python dependencies. Run: pip install -r requirements.txt"
    exit 1
fi
cd ..

# Test 2: Check Node dependencies
echo "📦 Checking Node.js dependencies..."
cd frontend
if [ -d "node_modules" ]; then
    echo -e "${GREEN}✓${NC} Node modules installed"
else
    echo -e "${RED}✗${NC} Missing Node modules. Run: npm install"
    exit 1
fi

# Test 3: Check environment variables
echo "🔑 Checking environment variables..."
if [ -f ".env.local" ]; then
    if grep -q "OPENAI_API_KEY" .env.local && \
       grep -q "NEXT_PUBLIC_HEYGEN_API_KEY" .env.local; then
        echo -e "${GREEN}✓${NC} Environment variables present"
    else
        echo -e "${YELLOW}⚠${NC}  Some API keys may be missing in .env.local"
    fi
else
    echo -e "${RED}✗${NC} No .env.local found in frontend/"
    exit 1
fi

# Check backend .env
cd ../backend
if [ -f ".env" ]; then
    if grep -q "ANTHROPIC_API_KEY" .env && \
       grep -q "GRB_WLSACCESSID" .env; then
        echo -e "${GREEN}✓${NC} Backend environment variables present"
    else
        echo -e "${YELLOW}⚠${NC}  Some backend keys may be missing in backend/.env"
    fi
else
    echo -e "${RED}✗${NC} No .env found in backend/"
    exit 1
fi
cd ../frontend

# Test 4: Next.js build
echo "🏗️  Testing Next.js build..."
if npm run build > /tmp/build.log 2>&1; then
    echo -e "${GREEN}✓${NC} Frontend builds successfully"
else
    echo -e "${RED}✗${NC} Build failed. Check /tmp/build.log"
    tail -20 /tmp/build.log
    exit 1
fi

# Test 5: Check Gurobi license
echo "🔐 Testing Gurobi license..."
cd ../backend
python -c "
import gurobipy as gp
try:
    env = gp.Env(empty=True)
    env.start()
    print('✓ Gurobi license valid')
except Exception as e:
    print(f'✗ Gurobi license error: {e}')
    exit(1)
" && GUROBI_OK=1 || GUROBI_OK=0

if [ $GUROBI_OK -eq 1 ]; then
    echo -e "${GREEN}✓${NC} Gurobi license activated"
else
    echo -e "${RED}✗${NC} Gurobi license error. Check WLS credentials"
    exit 1
fi

# Test 6: Check file structure
echo "📁 Verifying file structure..."
REQUIRED_DIRS=(
    "backend/current_query"
    "backend/data_upload"
    "backend/query_history"
    "frontend/.next"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "../$dir" ]; then
        echo -e "   ${GREEN}✓${NC} $dir exists"
    else
        echo -e "   ${RED}✗${NC} $dir missing"
        mkdir -p "../$dir"
        echo -e "   ${YELLOW}→${NC} Created $dir"
    fi
done

cd ..

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ All pre-deployment checks passed!${NC}"
echo ""
echo "Next steps:"
echo "1. Commit and push to GitHub:"
echo "   git add ."
echo "   git commit -m 'Ready for deployment'"
echo "   git push origin master"
echo ""
echo "2. Deploy to Render:"
echo "   - Go to https://dashboard.render.com/"
echo "   - Create new Web Service"
echo "   - Connect your GitHub repo"
echo "   - Follow DEPLOYMENT.md instructions"
echo ""
echo "3. Test deployed app with an optimization run"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
