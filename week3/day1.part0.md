# Day 1 Part 0: Getting Started with the Cybersecurity Analyzer

Welcome to Week 3 of AI in Production! Over the next two days, you'll deploy a real AI application to both Azure and Google Cloud Platform. By the end of Day 2, you'll have hands-on experience with modern cloud deployment practices used in production environments.

## What You'll Build

The **Cybersecurity Analyzer** is an AI-powered web application that analyzes Python code for security vulnerabilities. It combines:
- OpenAI's latest models for intelligent code analysis
- Semgrep for static security scanning
- A React/Next.js frontend
- A FastAPI backend
- Docker containerization
- Cloud deployment with Terraform

This is a real-world application architecture that you'll see in production environments!

---

## Section 1: Project Setup

### Clone the Repository

If you haven't already cloned the repository, do so now:

```bash
git clone https://github.com/ed-donner/cyber.git
```

### Open in Cursor

1. Launch Cursor
2. Click **File** → **New Window**
3. Click **Open Folder**
4. Navigate to and select the `cyber` folder you just cloned
5. Click **Open**

You should now see the project structure in Cursor's file explorer on the left.

Take a moment to explore the structure:
- `frontend/` - Next.js React application
- `backend/` - FastAPI Python server
- `terraform/` - Infrastructure as Code configurations
- `week3/` - These guides you're reading!

---

## Section 2: Semgrep Setup

Semgrep is a powerful static analysis tool that finds security vulnerabilities in code. Let's set up your account and get an API token.

### Create Your Semgrep Account

1. Visit https://semgrep.dev
2. Click **"Try Semgrep for free"** 
3. Click **"Continue with GitHub"**
4. Authorize Semgrep to connect with your GitHub account

### Generate Your API Token

Once logged into Semgrep:

1. Click **Settings** (bottom left corner of the dashboard)
2. In the main navigation, click **Tokens** and leave API tokens selected on the left  
3. Click **"Create New Token"**
4. Configure the token:
   - **Name** at the bottom: `cyber-analyzer` (or any name you like)
   - **Scopes**: Check both:
     - ✅ **Agent (CI)**
     - ✅ **Web API**
5. Click **"Create"**
6. **IMPORTANT**: Copy the token immediately! You won't be able to see it again.
   - It will look something like: `eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9...`

Keep this token handy - you'll need it in the next section.

---

## Section 3: Environment Configuration

Now let's create your `.env` file with the necessary API keys.

### Create the .env File

1. In Cursor, right-click on the project root (the `cyber` folder in the file explorer)
2. Select **"New File"**
3. Name it exactly `.env` (yes, starting with a dot)
4. Add the following content:

```
OPENAI_API_KEY=your-openai-key-here
SEMGREP_APP_TOKEN=your-semgrep-token-here
```

5. Replace the placeholder values:
   - `your-openai-key-here` - Your OpenAI API key from previous weeks
   - `your-semgrep-token-here` - The Semgrep token you just created
6. Save the file (`Cmd+S` on Mac, `Ctrl+S` on Windows/Linux)

⚠️ **Security Note**: The `.env` file is already in `.gitignore`, so it won't be committed to Git. Never share these keys publicly!

### Verify Your Keys

Your `.env` file should look similar to this (but with your actual keys):
```
OPENAI_API_KEY=sk-proj-abc123xyz...
SEMGREP_APP_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGc...
```

---

## Section 4: Test Locally Without Docker

Let's verify everything works by running the application locally.

### Prerequisites Check

First, ensure you have the required tools:

```bash
# Check Node.js (should be 20+)
node --version

# Check uv is installed (Python package manager)
uv --version
```

If `uv` is not installed:
```bash
# Mac/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (in PowerShell as admin)
irm https://astral.sh/uv/install.ps1 | iex
```

### Start the Backend Server

Open a terminal in Cursor (Terminal → New Terminal) and run:

```bash
cd backend
uv run server.py
```

You should see output like:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

The backend API is now running at http://localhost:8000

### Start the Frontend Development Server

Open a **new terminal** in Cursor (keep the backend running) and run:

```bash
cd frontend
npm install  # First time only
```
If you receive the output `found 0 vulnerabilities`, you can skip to [Test the Application](#test-the-application)

However, after running `npm install`, you _may_ receive a warning about vulnerabilities in some of the packages we have in our project dependencies. This is because, when you run `npm install`, an audit is automatically triggered, which checks your dependency list against a database containing a list of known vulnerabilities. At the time this code was written, the audit was clean (no vulerabilities), but if any new vulnerabilities have been identified since this code was written, they will be flagged for you as a warning, even though they may not even be reachable reachable in your app. If you wish to address the vulnerabilities, here are some steps you can follow:

1. Run an audit to see a full report
```bash
npm audit
```

2. Automatically apply any non-breaking fixes
```bash
npm audit fix
```

3. Re-run the audit to check what remains to be fixed
```bash
npm audit
```

4. Upgrade Next.js explicitly (rather than the suggested `npm audit fix --force`, which picks a version for you)
```bash
npm install next@latest eslint-config-next@latest
```

5. Check the results
```bash
npm ls next eslint-config-next
```

6. Build the app to prove your static export still produces valid output. We need to confirm everything works before we run the app or put it into a container image to be run.
```bash
npm run build
```

7. Run the audit one last time to confirm there are no more vulerabilities
```bash
npm audit
```

At this stage you should (hopefully) see the output:
```found 0 vulnerabilities```

If these steps still don't work for you, LLMs are great at helping to resolve issues like this. If you give your LLM chat access to your terminal window, it should be able to help resolve any warnings.

### Test the Application
Run your application locally

```bash
npm run dev
```
You should see output like:
```
  ▲ Next.js 16.3.1 (Turbopack)
  - Local:        http://localhost:3000
  - Environments: .env

✓ Ready in 2.1s
```

1. Open your browser to http://localhost:3000
   
   **Important**: Use the `http://localhost:3000` URL, not the IP address based URL that Next.js also displays. The application is configured to work with localhost in development mode.

2. You should see the Cybersecurity Analyzer interface
3. Click **"Choose File"** and select the `airline.py` file from the project root
   - This file contains intentional security vulnerabilities for testing
4. Click **"Analyze Code"**
5. It should take 1-2 minutes, then you should see multiple security vulnerabilities detected!

Note: if you see a warning like this on your server, you can safely ignore it; Semgrep would like you to upgrade to a Pro version, but that's not required for this project:  
`WARNING  User doesn't have the Pro Engine installed, not running `semgrep mcp` daemon...`    

Also - the first time you run this, Semgrep sometimes gives a timeout error while it's downloading resources. This seems to only happen after a fresh install, and not repeat. If you hit this, just try again. Let me know if this persists..

### Stopping the Servers

When you're done testing:
- Backend: Press `Ctrl+C` in the backend terminal
- Frontend: Press `Ctrl+C` in the frontend terminal

---

## Section 5: Test with Docker

Now let's test the containerized version - exactly what we'll deploy to the cloud!

### Prerequisites Check

Ensure Docker is installed and running:

```bash
docker --version
docker ps  # Should not error
```

If Docker isn't installed, download it from https://docker.com/get-started

### Build the Docker Image

In a terminal at the project root:

```bash
docker build -t cyber-analyzer .
```

This will take 2-5 minutes the first time as it:
- Downloads base images
- Installs Python dependencies
- Builds the Next.js frontend
- Packages everything together

You should see output ending with:
```
Successfully tagged cyber-analyzer:latest
```

### Run the Container

Start the containerized application:

```bash
docker run --rm --name cyber-analyzer -p 8000:8000 --env-file .env cyber-analyzer
```

Breaking down this command:
- `--rm`: Remove container when stopped
- `--name cyber-analyzer`: Name for easy reference
- `-p 8000:8000`: Map port 8000
- `--env-file .env`: Load environment variables
- `cyber-analyzer`: Image name

You'll see the server startup logs:
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Test the Container

1. Open http://localhost:8000 in your browser
2. Test by uploading the `airline.py` file from the project root
3. You should see the same security analysis results as before

### Stop the Container

When you're done testing, press `Ctrl+C` in the terminal to stop the container. It will be automatically removed (due to `--rm` flag).

---

## Troubleshooting

### "Module not found" or dependency errors
- Ensure you're using `uv run` for the backend (not just `python`)
- For frontend, run `npm install` before `npm run dev`

### "Port already in use"
- Check for other processes: `lsof -i :8000` (Mac/Linux) or `netstat -ano | findstr :8000` (Windows)
- Kill any conflicting processes or use different ports

### Docker build fails
- Ensure Docker Desktop is running
- Check available disk space: `docker system df`
- Clean up if needed: `docker system prune -a` (warning: removes all unused images)

### Environment variables not working
- Verify `.env` file is in project root (not in backend/ or frontend/)
- Check there are no spaces around the `=` in your `.env` file
- Ensure no quotes around the values unless they contain spaces

---

## What's Next?

🎉 **Congratulations!** You've successfully:
- ✅ Set up the Cybersecurity Analyzer project
- ✅ Configured Semgrep for security analysis
- ✅ Created your environment configuration
- ✅ Tested locally with both development servers
- ✅ Built and ran the Docker container

You're now ready to deploy this application to the cloud! 

**Next up**: [Day 1 Part 1: Azure Setup](./day1.part1.md) where you'll create your Azure account and prepare for cloud deployment.

The application you just tested locally will soon be running on Azure Container Apps and Google Cloud Run, accessible from anywhere in the world!