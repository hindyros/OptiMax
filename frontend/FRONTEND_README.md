# Optima Frontend

AI-Powered Mathematical Optimization Interface

## Setup Instructions

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

Edit `.env.local` and add your OpenAI API key:

```bash
OPENAI_API_KEY=sk-...your-key-here...
BACKEND_DIR=../backend
```

### 3. Start Development Server

```bash
npm run dev
```

The app will be available at [http://localhost:3000](http://localhost:3000)

## How It Works

### User Flow

1. **Landing Page** (`/`) - Introduction and "Start Optimizing" button
2. **Refinement** (`/refine`) - Conversational LLM interface
   - User describes problem in plain English
   - AI asks clarifying questions (up to 5 iterations)
   - **Confidence tracked internally, NEVER shown to user**
3. **Processing** (`/optimize/[jobId]`) - Real-time progress visualization
   - Shows OptiMUS pipeline stages
   - Polls status every second
4. **Results** (`/results/[jobId]`) - Final optimization results
   - Metric cards
   - Bar chart
   - Executive summary (markdown)
   - Technical details (LaTeX + code)

### Architecture

```
Frontend (Next.js)
├── API Routes (/app/api)
│   ├── /refine/start - Start LLM conversation
│   ├── /refine/continue - Continue conversation
│   ├── /optimize - Run OptiMUS pipeline
│   ├── /optimize/[jobId]/status - Check progress
│   └── /optimize/[jobId]/result - Get results
├── Pages (/app)
│   ├── / - Landing page
│   ├── /refine - LLM refinement chat
│   ├── /optimize/[jobId] - Progress visualization
│   └── /results/[jobId] - Results display
└── Backend Integration
    ├── Writes desc.txt and params.json
    ├── Runs `python optimus.py --clear`
    ├── Runs `python optimus.py`
    ├── Monitors state_*.json files
    ├── Runs `python judge.py`
    └── Reads verdict.json
```

### Key Features

**Hidden Confidence System**

- LLM tracks confidence (0-100%) internally
- Auto-proceeds when confidence ≥ 90% OR after 5 iterations
- **User NEVER sees confidence scores** - just smooth conversation

**Real-Time Progress**

- Polls state files every second
- Maps to progress percentages (0-100%)
- Shows user-friendly stage messages

**Professional Results**

- LaTeX math rendering (react-katex)
- Syntax-highlighted Python code (prism-react-renderer)
- Markdown-formatted explanations
- Simple bar chart (recharts)

## Testing

### Test with Sample Problem

Try this factory production problem:

```
A factory produces two products A and B. Product A yields $5 profit per unit,
product B yields $4 profit per unit. Each unit of A requires 2 hours of labor
and 1 unit of raw material. Each unit of B requires 1 hour of labor and 2 units
of raw material. The factory has 100 hours of labor and 80 units of raw material
available. Maximize total profit.
```

**Expected Results:**

- Optimal Profit: $280
- Product A: 20 units
- Product B: 40 units

## Troubleshooting

### API Routes Not Working

- Ensure you're running `npm run dev`
- Check that `.env.local` has `OPENAI_API_KEY` set

### Python Scripts Failing

- Verify backend dependencies are installed: `cd ../backend && pip install -r requirements.txt`
- Check that Gurobi license is configured
- Ensure Python is in PATH

### Progress Stuck

- Check backend logs in terminal
- Verify `current_query/optimus_output/` directory exists
- Try running `python ../backend/optimus.py --clear` manually

## Deployment

### Vercel (Recommended)

```bash
# Push to GitHub
git init
git add .
git commit -m "Initial commit"
git push

# Deploy to Vercel
vercel deploy --prod
```

Set environment variables in Vercel dashboard:

- `OPENAI_API_KEY=your_key_here`

## Technology Stack

- **Framework**: Next.js 14 (App Router, TypeScript)
- **Styling**: Tailwind CSS (Sublime dark theme)
- **LLM**: OpenAI GPT-4o (refinement)
- **Math**: react-katex (LaTeX rendering)
- **Code**: prism-react-renderer (syntax highlighting)
- **Charts**: recharts (bar chart)
- **Animations**: Framer Motion
- **Backend**: Python (OptiMUS + Gurobi)

## Project Structure

```
frontend/
├── app/
│   ├── api/               # Next.js API routes
│   │   ├── refine/
│   │   └── optimize/
│   ├── refine/            # LLM refinement page
│   ├── optimize/[jobId]/  # Progress page
│   ├── results/[jobId]/   # Results page
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Landing page
│   └── globals.css        # Sublime theme styles
├── lib/
│   ├── types.ts           # TypeScript interfaces
│   └── utils/
│       ├── python-runner.ts  # Spawn Python processes
│       ├── file-ops.ts       # Read/write backend files
│       ├── llm.ts            # OpenAI API integration
│       └── store.ts          # In-memory job/conversation storage
├── .env.local             # Environment variables
└── package.json           # Dependencies
```

## Demo Tips

1. **Start with landing page** - Shows professional first impression
2. **Use sample problem** - Factory production is quick to solve
3. **Highlight hidden confidence** - Explain how user never sees technical scores
4. **Show progress visualization** - Real-time updates are impressive
5. **Explain results** - LaTeX math + code show technical depth

## Credits

Built for TreeHacks 2024

- Frontend: Next.js + GPT-4
- Backend: OptiMUS optimization pipeline
- Solver: Gurobi
