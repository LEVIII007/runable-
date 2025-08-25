# Runable AI - Coding Agent

## What I've Actually Built

### 1. The Coding Agent (Kinda Works)

I built a coding agent using LangGraph that can:

- Take a task description and try to generate code for it
- Execute Python, JavaScript, and shell commands (with some basic safety checks)
- Create files and manage a workspace
- can open editor, terminal in GUI
- Run through multiple iterations trying to fix errors
- I have kept it limited to single file.
- no orchestration layer as of now, there is a single container where agent, noVNC, and other tools are running.
- **The catch:** Right now it only handles single files. No fancy multi-file projects yet. but it can be implemented.

### 2. LangGraph Workflow (Actually Pretty Cool)

We set up a proper workflow with these nodes:

- `initialize` - Sets up the task
- `generate_code` - Tries to write some code
- `execute_code` - Runs the code (if it's not too dangerous)
- `debug_code` - Tries to fix stuff when it breaks
- `analyze_results` - Looks at what happened
- `finalize` - Wraps it up

The agent can loop through these steps trying to get things working. It's not perfect, but it's a start.

### 3. Tools We Built (Some Work, Some Don't)

- **Shell execution** - Can run basic commands (with some safety checks)
- **Python execution** - Runs Python code in temp files
- **JavaScript execution** - Uses Node.js to run JS
- **File operations** - Create, read, list files
- **xdot/GUI stuff** - We have the infrastructure but haven't really used it yet

### 4. Docker Container

I built a Docker image that includes:

- Ubuntu 22.04 base
- xvfb (virtual display)
- x11vnc (VNC server)
- noVNC (web-based VNC viewer)
- Jupyter notebook
- xdot for GUI control
- gedit for text editing ( to show the code)

**The reality:** You can access it via VNC at `localhost:6080`, but we haven't really integrated the GUI tools into the agent workflow yet. It's there, just... sitting there.

### 5. Context Management (It's There, But Sloppy)

We built a context manager that:

- Stores conversation history, code, execution results
- Tries to be smart about what to keep (pruning old stuff)
- Saves everything to JSON files
- Has some basic importance scoring

**The honest truth:** It works, but it's not very sophisticated. We're not really using it effectively in the agent yet. The context gets stored but doesn't always get used properly.

### 6. Job Management (Actually Pretty Solid)

We built a job system with:

- `POST /schedule` endpoint to start coding tasks
- `GET /status/:id` to check progress
- Async job execution with ThreadPoolExecutor
- Job persistence (saves to JSON files)
- Download links for completed work (ZIP files)
- Basic job statistics and cleanup

This part actually works pretty well! You can submit tasks and track their progress.

## What We're Missing (The Honest Part)

### The Big Gaps:

1. **Multi-file projects** - Right now it's single files only
2. **GUI integration** - We have xdot and VNC but haven't connected them to the agent
3. **Better context usage** - The context manager exists but isn't really helping the agent make better decisions
4. **Real sandboxing** - We have basic safety checks but nothing like Firecracker VMs
5. **Horizontal scaling** - No k8s or Nomad integration yet

### The "It Works But..." Parts:

- Context management is there but not very smart
- GUI tools are installed but not integrated
- Code execution is basic (no real sandboxing)
- Error handling is... optimistic

## How to Run This Thing

1. **Set up your API keys:**

   ```bash
   echo "GOOGLE_API_KEY=your_gemini_key" > .env
   ```

2. **Build the Docker image:**

   ```bash
   docker build -t runable .
   ```

3. **Run it:**

   ```bash
   docker run -d --name runable -p 6080:6080 -p 8888:8888 -p 3000:3000 runable
   ```

4. **Access it:**
   - VNC viewer: `http://localhost:6080`
   - Jupyter: `http://localhost:8888`
   - API: `http://localhost:3000`

## The API Endpoints

- `POST /api/coding-agent/schedule` - Submit a coding task
- `GET /api/coding-agent/status/:id` - Check job status
- `GET /api/coding-agent/download/:filename` - Download results

## What's Next (If I Keep Going)

1. Actually integrate the GUI tools with the agent
2. Build proper multi-file project support
3. Implement real sandboxing (maybe Firecracker)
4. Make the context management actually useful
5. Add horizontal scaling with k8s/Nomad
6. more tools

## The Bottom Line

I've got about 50% of what was asked for. The foundation is there - the agent can generate and execute code, we have a job system, and the Docker container has all the tools. But it's rough around the edges and missing some key features.

but this architecture is not scalable at all.

# runable-gonna-hire-me?
