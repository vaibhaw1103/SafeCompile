# SafeCompile: AI-Powered Secure Code Compiler

A web-based IDE that uses a multi-layered approach, including LLMs and static analysis, to detect security vulnerabilities in C code before execution.

![SafeCompile Demo](https://via.placeholder.com/800x400.png?text=Add+A+Screenshot+Or+GIF+Here)


## ✨ Features

- **Multi-Layered Security Analysis**: Combines AI (via LLMs), machine learning (CodeBERT), a custom parser, and pattern matching for comprehensive vulnerability detection.
- **Sandboxed Execution**: User-submitted C code is compiled and run inside a secure, isolated Docker container to protect the host system.
- **Interactive Web UI**: A clean, modern interface built with Flask, Socket.IO, Monaco Editor (for a VS-Code like experience), and Xterm.js for a real-time terminal.
- **Real-time Feedback**: Get instant analysis results, compiler errors, and program output streamed directly to the UI.
- **Parse Tree Visualization**: Generates and displays a visual parse tree of the submitted code for educational and debugging purposes.

## 🛠️ Tech Stack

- **Backend**: Python, Flask, Flask-SocketIO
- **AI & ML**: OpenAI API (via OpenRouter), PyTorch, Transformers (CodeBERT), Scikit-learn
- **Execution Environment**: Docker
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Core Components**: Monaco Editor, Xterm.js, Gunicorn

## 🚀 How to Run Locally

Follow these steps to set up and run the project on your local machine.

### Prerequisites

- Python 3.9+
- Docker Desktop
- Git

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/vaibhaw1103/SafeCompile.git](https://github.com/vaibhaw1103/SafeCompile.git)
    cd SafeCompile
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your API Key:**
    The application loads your OpenRouter API key from an environment variable. You can set it in your terminal before running the app.
    
    **On macOS/Linux:**
    ```bash
    export OPENROUTER_API_KEY="your_secret_key_here"
    ```
    **On Windows (Command Prompt):**
    ```bash
    set OPENROUTER_API_KEY="your_secret_key_here"
    ```

5.  **Run the application:**
    ```bash
    python app.py
    ```

Open your browser and navigate to `http://127.0.0.1:5000` to see the application live.