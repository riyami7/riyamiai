# Ollama Cheat Sheet

A comprehensive reference guide for Ollama commands and server management.

---

## Server Management

### Start Server in Background

Start the Ollama server as a background process:

```bash
ollama serve &
```

**Note:** If you installed Ollama as a desktop application, it likely runs as a background service by default, so you may not need to run this manually.

---

### Check if Server is Running

**Option 1: Check server process**

```bash
pgrep -a ollama
```

The `-a` flag shows the full command line of the running process.

**Option 2: List loaded models**

```bash
ollama ps
```

This command lists any models currently loaded in memory, indicating that the server is active.

**Option 3: Test server endpoint**

```bash
curl http://127.0.0.1:11434/api/tags
```

Returns a list of available models if the server is running.

---

### Stop Server

**Option 1: Kill the process**

```bash
pkill ollama
```

**Option 2: On macOS Desktop App**

Click the Ollama icon in the menu bar and select **"Quit Ollama"**.

---

## Model Management

### List Available Models

```bash
ollama list
```

Shows all models you have downloaded locally.

---

### Pull/Download a Model

```bash
ollama pull <model-name>
```

**Examples:**

```bash
ollama pull llama3.2
ollama pull mistral
ollama pull codellama
```

---

### Remove a Model

```bash
ollama rm <model-name>
```

**Example:**

```bash
ollama rm llama3.2
```

---

### Show Model Information

```bash
ollama show <model-name>
```

Displays detailed information about a specific model including architecture, parameters, and template.

---

## Running Models

### Run a Model Interactively

```bash
ollama run <model-name>
```

**Example:**

```bash
ollama run llama3.2
```

This starts an interactive chat session with the model.

---

### Run with a Single Prompt

```bash
ollama run <model-name> "<your-prompt>"
```

**Example:**

```bash
ollama run llama3.2 "Explain what Ollama is"
```

---

### Exit Interactive Mode

Type `/bye` or press `Ctrl+D` to exit the interactive chat.

---

## API Usage

### Default API Endpoint

```
http://127.0.0.1:11434
```

---

### Generate Completion (API)

```bash
curl http://127.0.0.1:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?"
}'
```

---

### Chat Completion (API)

```bash
curl http://127.0.0.1:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ]
}'
```

---

## Advanced Commands

### Create Custom Model

```bash
ollama create <custom-model-name> -f <Modelfile>
```

**Example:**

```bash
ollama create mymodel -f ./Modelfile
```

---

### Copy a Model

```bash
ollama cp <source-model> <destination-model>
```

**Example:**

```bash
ollama cp llama3.2 my-llama
```

---

### Check Ollama Version

```bash
ollama --version
```

or

```bash
ollama -v
```

---

## Environment Variables

### Set Custom Server Address

```bash
export OLLAMA_HOST=0.0.0.0:11434
```

Then start the server:

```bash
ollama serve
```

---

### Set Models Directory

```bash
export OLLAMA_MODELS=/path/to/models
```

---

## Useful Tips

- **Models Storage Location (macOS):** `~/.ollama/models`
- **Models Storage Location (Linux):** `/usr/share/ollama/.ollama/models`
- **Default Port:** `11434`
- **Server runs on:** `http://127.0.0.1:11434` by default

---

## Common Model Names

| Model | Description | Size |
|-------|-------------|------|
| `llama3.2` | Latest Llama model | Various sizes |
| `mistral` | Mistral AI model | 7B parameters |
| `codellama` | Code-specialized Llama | Various sizes |
| `gemma` | Google's Gemma model | Various sizes |
| `phi` | Microsoft's Phi model | Small, efficient |
| `qwen` | Alibaba's Qwen model | Various sizes |
| `aya` | Multilingual model | Good for Arabic |

---

## Troubleshooting

### Server not responding?

```bash
# Check if process is running
pgrep -a ollama

# Check server logs (if running in foreground)
ollama serve

# Restart the server
pkill ollama
ollama serve &
```

---

### Port already in use?

```bash
# Find what's using port 11434
lsof -i :11434

# Use a different port
export OLLAMA_HOST=0.0.0.0:11435
ollama serve
```

---

## Quick Reference Card

```bash
# Start server
ollama serve &

# Check server
pgrep -a ollama
ollama ps

# Stop server
pkill ollama

# List models
ollama list

# Download model
ollama pull llama3.2

# Run model
ollama run llama3.2

# Remove model
ollama rm llama3.2

# Check version
ollama --version
```

---

**Last Updated:** February 2026  
**Ollama Version:** 0.15.5+
