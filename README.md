# Llama-Term: Interactive LLM Command Runner

Llama-Term is an interactive Python tool that leverages the Ollama API running Llama 3.2 to generate and execute Unix commands based on plain-English user instructions. It supports multi-turn clarifications, automatic Linux distribution detection, package manager validation, interactive command execution (with streaming output), and error recovery (such as creating missing groups).

## Features

- **Interactive Command Generation:**  
  Describe your goal in plain language (e.g., "add this user to docker group") and get back a Unix command suggestion.

- **Multi-turn Clarification:**  
  If the LLM needs more details, it will ask you a clarifying question. You can provide additional input or type `cancel` to abort the process.

- **Linux Distribution Detection:**  
  Automatically reads `/etc/os-release` to determine your specific distro and maps it to a broad family (e.g., "Arch-based" or "Ubuntu/Debian-based"). This information is passed to the LLM to generate context-aware commands.

- **Package Manager Validation:**  
  If the command involves package management, the script checks that the suggested command uses the appropriate package manager for your distro family.

- **Interactive Command Execution:**  
  Commands are executed interactively, streaming output to your terminal so you can interact with prompts (for example, answering `[Y/n]` questions).

- **Error Recovery:**  
  Common error cases are handled automatically. For example, if you try to add a user to the `docker` group and that group does not exist, the script will ask if you want to create it and then re-run the command.

## Prerequisites

- **Python 3.6+**  
- The [requests](https://pypi.org/project/requests/) library (`pip install requests`)

- **Ollama API:**  
  An instance of Ollama running Llama 3.2 must be accessible. Update the API endpoint in the script (`OLLAMA_HOST` and `OLLAMA_PORT`) as needed.

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/llama-term.git
   cd llama-term
   ```

2. **Install dependencies:**

   ```bash
   pip install requests
   ```

3. **Configure the Ollama API endpoint:**  
   Edit `llama-term.py` if necessary to update `OLLAMA_HOST` and `OLLAMA_PORT`.

## Usage

Run the script:

```bash
python3 llama-term.py
```

### How It Works

1. **Describe Your Goal:**  
   The script prompts you:
   ```
   Describe what you want to accomplish:
   > add this user to docker group
   ```

2. **LLM Command Suggestion:**  
   The script queries the LLM with your instruction (including the broad distro family) and displays the suggested command:
   ```
   Final command suggested by LLM:
   ----------------------------------------
   usermod -aG docker username
   ----------------------------------------
   Execute this command? (Y/n):
   ```

3. **Interactive Execution:**  
   The command is executed interactively. If errors occur (e.g., "group 'docker' does not exist"), the script prompts you:
   ```
   It appears the docker group does not exist. Would you like to create it? (Y/n):
   ```

4. **Error Recovery:**  
   On confirmation, the script creates the group and re-runs the original command.

## Customization

- **Base Prompt:**  
  Modify the `BASE_PROMPT` variable in the script to change how the LLM is instructed.

- **Error Handling:**  
  You can adjust the heuristics for package manager checks and error recovery as needed.

## Example Session

```bash
Describe what you want to accomplish:
> add this user to docker group

Querying LLM for a command suggestion...

Final command suggested by LLM:
----------------------------------------
usermod -aG docker username
----------------------------------------
Execute this command? (Y/n): y
usermod: group 'docker' does not exist
Command exited with return code 6.
It appears the docker group does not exist. Would you like to create it? (Y/n): y
Docker group created successfully. Re-running the original command...
Command executed successfully after creating docker group.
```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Feel free to fork the repository and submit pull requests with improvements or bug fixes.

## Acknowledgments

- Thanks to the Llama 3.2 model via Ollama for the underlying language generation.
- Inspired by the need for an interactive, context-aware command runner for Linux systems.
