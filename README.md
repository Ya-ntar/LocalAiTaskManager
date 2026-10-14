# CONTEXT
This is mainly a vibe-coded prototype to test what I want and whether or not it is achievable on the local machine. I've started it spontaniously (and because i couldnt find an instrument that would do i wanted it to do), and its not very thought out. Its 
my first experience with relying so much on agents, and im doing it in most inefficient ways. I also havent worked on any creation of ai-powered apps before and experimenting with architecture of a whole thing.
# LocalAiTaskManager

A task manager with a local AI assistant. Run the AI model on your own computer and use it to create, organize, prioritize, and work with tasks without sending your task data to a hosted AI provider.

## What you need

- Python 3.10 or newer
- Node.js 18 or newer and npm, if the frontend is included in your checkout
- A local AI runtime that exposes an HTTP API
- Git

The easiest local provider to use is [Ollama](https://ollama.com/). [LM Studio](https://lmstudio.ai/) and other OpenAI-compatible local servers can also be used when configured with their local API address.

## Installation

Clone the repository and create a Python virtual environment:

```bash
git clone https://github.com/Ya-ntar/LocalAiTaskManager.git
cd LocalAiTaskManager

python -m venv .venv
```

Activate the environment:

### Windows PowerShell

```powershell
.\.venv\Scripts\Activate.ps1
```

### macOS/Linux

```bash
source .venv/bin/activate
```

Install the Python dependencies if a requirements file is present:

```bash
pip install -r requirements.txt
```

If the project includes a JavaScript frontend, install its dependencies from the frontend directory:

```bash
npm install
```

## Connect a local AI model

The task manager needs two things from your local AI runtime:

1. **A model name**, such as `llama3.2`.
2. **The local API URL**, usually an address on `localhost`.

Keep the model server running before starting the task manager.

### Option 1: Ollama

1. Install and start Ollama.
2. Download a model:

   ```bash
   ollama pull llama3.2
   ```

3. Verify that the model responds:

   ```bash
   ollama run llama3.2
   ```

4. Configure the application to use:

   ```text
   Provider: Ollama
   Model: llama3.2
   Base URL: http://127.0.0.1:11434
   ```

Ollama's API is normally available at `http://127.0.0.1:11434`. If the application uses environment variables for its AI settings, use values equivalent to:

```env
AI_PROVIDER=ollama
AI_MODEL=llama3.2
AI_BASE_URL=http://127.0.0.1:11434
```

Do not add an API key for a local Ollama server unless your local proxy specifically requires one.

### Option 2: LM Studio or another OpenAI-compatible server

1. Download a model in LM Studio or your preferred local runtime.
2. Start its local server.
3. Enable its OpenAI-compatible API.
4. Point the application at the server's displayed URL. A common LM Studio URL is:

   ```text
   http://127.0.0.1:1234/v1
   ```

Example configuration:

```env
AI_PROVIDER=openai-compatible
AI_MODEL=<the-model-name-shown-by-your-server>
AI_BASE_URL=http://127.0.0.1:1234/v1
AI_API_KEY=local
```

The API key is often ignored by local servers, but setting a placeholder such as `local` can be necessary for clients that require the field. Use the exact model identifier reported by your local server.

The application also accepts `AI_API_URL` and `AI_MODEL` environment variables. Set them to the exact OpenAI-compatible endpoint and model identifier shown by LM Studio, for example:

```powershell
$env:AI_API_URL = "http://127.0.0.1:1234/v1/chat/completions"
$env:AI_MODEL = "qwen2.5-7b-instruct-1m"
```

The `41343` port in LM Studio startup logs is an internal LM Studio API port. It is not the endpoint used by this application.

## Start the application

Use the project’s Python entry point to start the backend. For example:

```bash
python app.py
```

If the repository uses a different entry point, start the Python module or script shown in the project files. For a frontend, run it in a second terminal:

```bash
npm run dev
```

Open the local address printed in the terminal, commonly `http://127.0.0.1:8000` or `http://localhost:3000`.

## Recommended first run

1. Start Ollama or your OpenAI-compatible local server.
2. Confirm that the selected model is downloaded and available.
3. Start LocalAiTaskManager.
4. Open the settings or configuration screen and enter the local provider, model, and base URL.
5. Create a test task and ask the assistant to summarize or prioritize it.
6. If the assistant does not respond, check the troubleshooting section below and the terminal output from both applications.

## Troubleshooting

### Connection refused

Make sure the local model server is running and that the base URL includes the correct port. Test Ollama with:

```bash
curl http://127.0.0.1:11434/api/tags
```

For an OpenAI-compatible server, check its server log and copy the URL shown there. Do not use `localhost` from a container unless the model server is running inside the same container; use the host address appropriate for your setup instead.

### Model not found

List the models available in Ollama:

```bash
ollama list
```

Then set `AI_MODEL` to one of the returned names, or download the model named in your configuration with `ollama pull <model-name>`.

### Slow responses or out-of-memory errors

Use a smaller or quantized model, close other applications using GPU memory, and reduce the context length or response size in the local AI server. Local inference speed depends on your CPU, GPU, available RAM, and model size.

### The application starts but the assistant is unavailable

Check all of the following:

- The AI server was started before the task manager.
- The configured provider matches the server API format.
- The model name is spelled exactly as shown by the server.
- The base URL uses the correct port and, for OpenAI-compatible servers, includes `/v1` when required.
- Your firewall is allowing local connections.
- The backend terminal does not show an authentication, timeout, or JSON/API-version error.

## Privacy

When configured to use Ollama or another local server, prompts and task data are sent to the local service on your machine. Review the selected model server's configuration before exposing its API beyond your computer or local network.

## Development

Keep the local AI server running while developing so that assistant features can be tested end to end. Avoid committing `.env` files, downloaded model files, virtual environments, or API keys:

```gitignore
.env
.venv/
node_modules/
```

## License

No license is currently specified for this repository. Add a license before redistributing the project or accepting external contributions.
