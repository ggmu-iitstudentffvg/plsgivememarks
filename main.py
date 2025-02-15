from fastapi import FastAPI, HTTPException
import subprocess
import os
import json
import datetime
import sqlite3
import requests

app = FastAPI()

AI_PROXY_TOKEN = os.getenv("AIPROXY_TOKEN", "")

# Helper function to check if a file exists
def file_exists(path):
    return os.path.exists(path) and os.path.isfile(path)

# A1: Install uv (if required) and run datagen.py
def is_uv_installed():
    try:
        subprocess.run(["uv", "--version"], check=True, capture_output=True, text=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_uv():
    subprocess.run(["pip", "install", "uv"], check=True)

def download_datagen():
    url = "https://raw.githubusercontent.com/sanand0/tools-in-data-science-public/tds-2025-01/project-1/datagen.py"
    response = requests.get(url)
    if response.status_code == 200:
        with open("datagen.py", "w", encoding="utf-8") as file:
            file.write(response.text)
        return True
    return False

def run_datagen(user_email: str):
    subprocess.run(["python", "datagen.py", user_email], check=True)

# A2: Format /data/format.md using prettier
def format_markdown():
    if not file_exists("/data/format.md"):
        raise HTTPException(status_code=404, detail="File /data/format.md not found")
    subprocess.run(["npx", "prettier@3.4.2", "--write", "/data/format.md"], check=True)

# A3: Count number of Wednesdays in /data/dates.txt
def count_wednesdays():
    if not file_exists("/data/dates.txt"):
        raise HTTPException(status_code=404, detail="File /data/dates.txt not found")
    with open("/data/dates.txt", "r") as file:
        dates = file.readlines()
    
    wednesday_count = sum(1 for date in dates if datetime.datetime.strptime(date.strip(), "%Y-%m-%d").weekday() == 2)
    
    with open("/data/dates-wednesdays.txt", "w") as output_file:
        output_file.write(str(wednesday_count))

# A4: Sort contacts by last_name, then first_name
def sort_contacts():
    if not file_exists("/data/contacts.json"):
        raise HTTPException(status_code=404, detail="File /data/contacts.json not found")
    with open("/data/contacts.json", "r") as file:
        contacts = json.load(file)
    
    contacts_sorted = sorted(contacts, key=lambda x: (x["last_name"], x["first_name"]))
    
    with open("/data/contacts-sorted.json", "w") as output_file:
        json.dump(contacts_sorted, output_file, indent=2)

# A5: Get first line of the 10 most recent .log files
def recent_log_lines():
    log_dir = "/data/logs/"
    if not os.path.exists(log_dir):
        raise HTTPException(status_code=404, detail="Logs directory not found")
    
    log_files = sorted(
        [os.path.join(log_dir, f) for f in os.listdir(log_dir) if f.endswith(".log")],
        key=os.path.getmtime, reverse=True
    )[:10]

    lines = []
    for file in log_files:
        with open(file, "r") as f:
            lines.append(f.readline().strip())

    with open("/data/logs-recent.txt", "w") as output_file:
        output_file.write("\n".join(lines))

# A6: Extract H1 titles from Markdown files
def generate_md_index():
    doc_dir = "/data/docs/"
    if not os.path.exists(doc_dir):
        raise HTTPException(status_code=404, detail="Docs directory not found")
    
    index = {}
    for file in os.listdir(doc_dir):
        if file.endswith(".md"):
            with open(os.path.join(doc_dir, file), "r") as f:
                for line in f:
                    if line.startswith("# "):
                        index[file] = line[2:].strip()
                        break

    with open("/data/docs/index.json", "w") as output_file:
        json.dump(index, output_file, indent=2)

# A7: Extract sender’s email address using LLM
def extract_email_sender():
    if not file_exists("/data/email.txt"):
        raise HTTPException(status_code=404, detail="File /data/email.txt not found")
    with open("/data/email.txt", "r") as file:
        email_content = file.read()

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {AI_PROXY_TOKEN}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": "Extract the sender's email address."},
                         {"role": "user", "content": email_content}]
        }
    )

    email_address = response.json()["choices"][0]["message"]["content"].strip()
    with open("/data/email-sender.txt", "w") as output_file:
        output_file.write(email_address)

# A8: Extract credit card number from image using LLM
def extract_credit_card():
    if not file_exists("/data/credit-card.png"):
        raise HTTPException(status_code=404, detail="File /data/credit-card.png not found")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {AI_PROXY_TOKEN}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": "Extract the credit card number from this image."}],
            "image": "/data/credit-card.png"
        }
    )

    card_number = response.json()["choices"][0]["message"]["content"].replace(" ", "")
    with open("/data/credit-card.txt", "w") as output_file:
        output_file.write(card_number)

# A9: Find most similar pair of comments
def find_similar_comments():
    if not file_exists("/data/comments.txt"):
        raise HTTPException(status_code=404, detail="File /data/comments.txt not found")

    with open("/data/comments.txt", "r") as file:
        comments = file.readlines()

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {AI_PROXY_TOKEN}"},
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "system", "content": "Find the most similar pair of comments."},
                         {"role": "user", "content": "\n".join(comments)}]
        }
    )

    similar_comments = response.json()["choices"][0]["message"]["content"].split("\n")
    with open("/data/comments-similar.txt", "w") as output_file:
        output_file.write("\n".join(similar_comments))

# A10: Compute total sales for “Gold” tickets
def compute_gold_sales():
    if not file_exists("/data/ticket-sales.db"):
        raise HTTPException(status_code=404, detail="Database file not found")
    
    conn = sqlite3.connect("/data/ticket-sales.db")
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(units * price) FROM tickets WHERE type = 'Gold'")
    total_sales = cursor.fetchone()[0]
    conn.close()

    with open("/data/ticket-sales-gold.txt", "w") as output_file:
        output_file.write(str(total_sales))

# API Route
@app.post("/run")
async def run_task(task: str):
    if "format markdown" in task.lower():
        format_markdown()
    elif "count wednesdays" in task.lower():
        count_wednesdays()
    elif "sort contacts" in task.lower():
        sort_contacts()
    elif "recent logs" in task.lower():
        recent_log_lines()
    elif "markdown index" in task.lower():
        generate_md_index()
    elif "extract email" in task.lower():
        extract_email_sender()
    elif "credit card" in task.lower():
        extract_credit_card()
    elif "similar comments" in task.lower():
        find_similar_comments()
    elif "gold sales" in task.lower():
        compute_gold_sales()
    else:
        raise HTTPException(status_code=400, detail="Invalid task")

    return {"status": "success"}
