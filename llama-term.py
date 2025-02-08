#!/usr/bin/env python3
import json
import os
import re
import requests
import subprocess
import sys

# ------------------------
# Utility: Determine distro and broad family
# ------------------------
def get_distro_and_family():
    distro = "unknown"
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    distro = line.split("=")[1].strip().strip('"').lower()
                    break
    except Exception as e:
        print("Couldn't determine distro:", e)
    # Map specific distro IDs to broad families.
    if distro in ["ubuntu", "debian", "mint", "elementary", "pop"]:
        family = "Ubuntu/Debian-based"
    elif distro in ["endeavouros", "arch", "manjaro"]:
        family = "Arch-based"
    elif distro in ["fedora", "centos", "rhel"]:
        family = "Fedora/RHEL-based"
    else:
        family = distro
    return distro, family

# ------------------------
# Check that a command is appropriate for the distro family (only for package management commands)
# ------------------------
def is_command_for_distro(cmd, family):
    """
    If the command contains any package management keywords (apt, pacman, etc.), then
    ensure that it matches the expected package manager for the detected broad family.
    Otherwise, accept the command as generic.
    """
    cmd_lower = cmd.lower()
    pm_keywords = ["apt", "apt-get", "dpkg", "pacman", "dnf", "yum"]
    expected_pm = {
         "Ubuntu/Debian-based": ["apt", "apt-get", "dpkg"],
         "Arch-based": ["pacman"],
         "Fedora/RHEL-based": ["dnf", "yum"],
    }
    if any(keyword in cmd_lower for keyword in pm_keywords):
         if family in expected_pm:
             if any(keyword in cmd_lower for keyword in expected_pm[family]):
                  return True
             else:
                  return False
         else:
             return True
    else:
         return True

# ------------------------
# Configuration for Ollama
# ------------------------
OLLAMA_HOST = "10.0.0.100"
OLLAMA_PORT = 11434  # adjust if needed
OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}/api/generate"

# ------------------------
# Base prompt instructions
# ------------------------
BASE_PROMPT = (
    "You are a Unix command line assistant. "
    "Your job is to generate command line commands for the user. "
    "If you have enough information, respond ONLY with the Unix command enclosed in backticks (for example, `mkdir test`) and nothing else. "
    "If you need clarification, ask a single clarifying question ending with a question mark (?).\n"
)

# ------------------------
# Build the conversation prompt (includes the broad distro family)
# ------------------------
def build_prompt(conversation_history, family):
    prompt = BASE_PROMPT + "\n"
    prompt += f"System distribution: {family}\n"
    for entry in conversation_history:
        prompt += entry + "\n"
    return prompt

# ------------------------
# Query Ollama (with streaming JSON lines)
# ------------------------
def query_ollama(prompt):
    payload = {
        "model": "llama3.2",
        "prompt": prompt,
        "parameters": {
            "max_tokens": 150,
            "temperature": 0.7
        }
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True)
        response.raise_for_status()
        output_parts = []
        for line in response.iter_lines(decode_unicode=True):
            if line:
                try:
                    data = json.loads(line)
                    output_parts.append(data.get("response", ""))
                    if data.get("done", False):
                        break
                except json.JSONDecodeError as je:
                    print(f"JSON decode error: {je}")
                    continue
        return ''.join(output_parts).strip()
    except Exception as e:
        print(f"Error communicating with Ollama: {e}")
        return None

# ------------------------
# Extract a command from the LLM response
# ------------------------
def extract_command(response_text):
    """
    Look for a command enclosed in backticks or in triple-backtick code blocks.
    """
    match = re.search(r'`([^`]+)`', response_text)
    if match:
        return match.group(1).strip()
    match = re.search(r'```([\s\S]+?)```', response_text)
    if match:
        return match.group(1).strip()
    return ""

# ------------------------
# Check for a valid command line command (generic heuristics)
# ------------------------
def is_valid_command(cmd):
    cmd = cmd.strip()
    if not cmd:
        return False
    if "\n" in cmd:
        return False
    lower = cmd.lower()
    conversation_starters = ("it ", "i'm", "hello", "hi", "sure", "ok", "yes")
    for starter in conversation_starters:
        if lower.startswith(starter):
            return False
    if "command:" in lower or "output:" in lower:
        return False
    return True

# ------------------------
# Execute a shell command interactively (streams output to terminal)
# ------------------------
def execute_command(command):
    """
    Execute the command interactively, streaming output to the terminal.
    This lets you interact with the process if it prompts for input.
    """
    try:
        result = subprocess.run(command, shell=True)
        return result.returncode, None, None
    except Exception as e:
        return -1, None, str(e)

# ------------------------
# Main loop
# ------------------------
def main():
    distro, family = get_distro_and_family()
    print(f"Detected system distribution: {distro} ({family})")
    print("Interactive LLM Command Runner. Type 'exit' to quit.")

    while True:
        user_instruction = input("\nDescribe what you want to accomplish:\n> ").strip()
        if user_instruction.lower() in ("exit", "quit"):
            print("Exiting.")
            break

        conversation_history = []
        conversation_history.append("User: " + user_instruction)
        final_command = None
        iteration = 0
        max_iterations = 5

        while iteration < max_iterations:
            prompt = build_prompt(conversation_history, family)
            print("\nQuerying LLM for a command suggestion...")
            llm_response = query_ollama(prompt)
            if not llm_response:
                print("No response received. Aborting this request.")
                break

            candidate = extract_command(llm_response)
            if candidate and is_valid_command(candidate):
                if not is_command_for_distro(candidate, family):
                    expected = ("apt/dpkg" if family == "Ubuntu/Debian-based"
                                else ("dnf/yum" if family == "Fedora/RHEL-based"
                                      else "the distro's package manager"))
                    print("LLM returned a command that appears to be a package management command not matching your distro family.")
                    print(f"Received: {candidate}")
                    print(f"Expected a command using {expected} if a package manager is involved.")
                    clarification = input("Your clarification (or type 'cancel' to abort): ").strip()
                    if clarification.lower() in ("cancel", "break", "exit", "quit"):
                        print("Clarification loop aborted.")
                        final_command = None
                        break
                    if not clarification:
                        print(f"No clarification provided. Please specify if this is a package management command or a generic one.")
                        continue
                    conversation_history.append("Assistant (mismatch): " + llm_response)
                    conversation_history.append("User: " + clarification)
                    iteration += 1
                    continue
                else:
                    final_command = candidate
                    conversation_history.append("Assistant: " + llm_response)
                    break
            else:
                if llm_response.strip().endswith("?"):
                    print("LLM asks:", llm_response)
                    clarification = input("Your clarification (or type 'cancel' to abort): ").strip()
                    if clarification.lower() in ("cancel", "break", "exit", "quit"):
                        print("Clarification loop aborted.")
                        final_command = None
                        break
                    if not clarification:
                        print("No clarification provided. Please provide additional details.")
                        continue
                    conversation_history.append("Assistant: " + llm_response)
                    conversation_history.append("User: " + clarification)
                    iteration += 1
                    continue
                else:
                    print("LLM did not return a valid command. Please try rephrasing your request.")
                    final_command = None
                    break

        if not final_command:
            print("No valid command generated. Starting over.")
            continue

        print("\nFinal command suggested by LLM:")
        print("----------------------------------------")
        print(final_command)
        print("----------------------------------------")
        confirm = input("Execute this command? (Y/n): ").strip().lower()
        if confirm not in ("y", "yes", ""):
            print("Command skipped.")
            continue

        retcode, _, _ = execute_command(final_command)
        # Check for the common error when adding a user to a group if the group doesn't exist.
        if retcode != 0 and "usermod" in final_command.lower() and "docker" in final_command.lower():
            create_group = input("It appears the docker group does not exist. Would you like to create it? (Y/n): ").strip().lower()
            if create_group in ("y", "yes", ""):
                retcode2, _, _ = execute_command("sudo groupadd docker")
                if retcode2 == 0:
                    print("Docker group created successfully. Re-running the original command.")
                    retcode, _, _ = execute_command(final_command)
                    if retcode != 0:
                        print(f"Command exited with return code {retcode} after creating docker group.")
                    else:
                        print("Command executed successfully after creating docker group.")
                else:
                    print("Failed to create docker group.")
            else:
                print("Command aborted due to missing docker group.")
        elif retcode != 0:
            # Fallback: if permission was denied, ask if you want to re-run with sudo.
            sudo_confirm = input("Command error occurred. Try running with sudo? (Y/n): ").strip().lower()
            if sudo_confirm in ("y", "yes", ""):
                if not final_command.strip().startswith("sudo"):
                    final_command = "sudo " + final_command
                retcode, _, _ = execute_command(final_command)
                if retcode != 0:
                    print(f"Command exited with return code {retcode}.")
                else:
                    print("Command executed successfully with sudo.")
            else:
                print(f"Command exited with return code {retcode}.")
        else:
            print("Command executed successfully.")

if __name__ == "__main__":
    main()
