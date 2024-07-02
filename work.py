import subprocess
import re
from datetime import datetime, timedelta
import os
import requests
import json
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Twitch theme colors
BACKGROUND_COLOR = "#9147FF"
FOREGROUND_COLOR = "#FFFFFF"
BUTTON_COLOR = "#6441A4"
ENTRY_BACKGROUND_COLOR = "#4B367C"

app = tk.Tk()
app.title("Twitch Chat Downloader and Filter")
app.configure(bg=BACKGROUND_COLOR)

tk.Label(app, text="Twitch VOD URL:", bg=BACKGROUND_COLOR, fg=FOREGROUND_COLOR).grid(row=0, column=0, padx=10, pady=5, sticky='e')
vod_url_entry = tk.Entry(app, width=50, bg=ENTRY_BACKGROUND_COLOR, fg=FOREGROUND_COLOR)
vod_url_entry.grid(row=0, column=1, padx=10, pady=5, sticky='w')

tk.Label(app, text="Seconds to Add/Subtract:", bg=BACKGROUND_COLOR, fg=FOREGROUND_COLOR).grid(row=1, column=0, padx=10, pady=5, sticky='e')
add_seconds_entry = tk.Entry(app, width=10, bg=ENTRY_BACKGROUND_COLOR, fg=FOREGROUND_COLOR)
add_seconds_entry.grid(row=1, column=1, padx=10, pady=5, sticky='w')

tk.Label(app, text="Usernames to Filter (comma-separated):", bg=BACKGROUND_COLOR, fg=FOREGROUND_COLOR).grid(row=2, column=0, padx=10, pady=5, sticky='e')
filter_users_entry = tk.Entry(app, width=50, bg=ENTRY_BACKGROUND_COLOR, fg=FOREGROUND_COLOR)
filter_users_entry.grid(row=2, column=1, padx=10, pady=5, sticky='w')

start_button = tk.Button(app, text="Start Processing", bg=BUTTON_COLOR, fg=FOREGROUND_COLOR)
start_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)

download_label = tk.Label(app, text="Download Progress:", bg=BACKGROUND_COLOR, fg=FOREGROUND_COLOR)
download_progress = ttk.Progressbar(app, orient='horizontal', mode='determinate', length=300)

read_label = tk.Label(app, text="Read Progress:", bg=BACKGROUND_COLOR, fg=FOREGROUND_COLOR)
read_progress = ttk.Progressbar(app, length=300, mode='determinate')

filter_label = tk.Label(app, text="Filter Progress:", bg=BACKGROUND_COLOR, fg=FOREGROUND_COLOR)
filter_progress = ttk.Progressbar(app, orient="horizontal", length=300, mode="determinate")

filtered_messages_text = tk.Text(app, width=60, height=20, bg=BACKGROUND_COLOR, fg=FOREGROUND_COLOR)
filtered_messages_text.configure(font=("Helvetica", 12))

def save_text():
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
    if file_path:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(filtered_messages_text.get("1.0", tk.END))
        messagebox.showinfo("Success", "Text saved successfully!")
        hide_text_area_and_progress_bars()
        start_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10)  # Re-show the start button

save_button = tk.Button(app, text="Save Text", bg=BUTTON_COLOR, fg=FOREGROUND_COLOR, command=save_text)

def display_filtered_messages(filtered_messages):
    filtered_messages_text.grid(row=7, column=0, columnspan=2, padx=10, pady=10)
    filtered_messages_text.delete('1.0', tk.END)
    for message in filtered_messages:
        filtered_messages_text.insert(tk.END, message + '\n')
    save_button.grid(row=8, column=0, columnspan=2, padx=10, pady=10)

def hide_text_area_and_progress_bars():
    download_label.grid_remove()
    download_progress.grid_remove()
    read_label.grid_remove()
    read_progress.grid_remove()
    filter_label.grid_remove()
    filter_progress.grid_remove()
    filtered_messages_text.grid_remove()
    save_button.grid_remove()

def show_progress_bars():
    download_label.grid(row=4, column=0, padx=10, pady=5, sticky='e')
    download_progress.grid(row=4, column=1, padx=10, pady=5, sticky='w')
    read_label.grid(row=5, column=0, padx=10, pady=5, sticky='e')
    read_progress.grid(row=5, column=1, padx=10, pady=5, sticky='w')
    filter_label.grid(row=6, column=0, padx=10, pady=5, sticky='e')
    filter_progress.grid(row=6, column=1, padx=10, pady=5, sticky='w')

def start_processing():
    vod_url = vod_url_entry.get()
    add_seconds = add_seconds_entry.get()
    filter_users = filter_users_entry.get()

    if not vod_url or not add_seconds or not filter_users:
        messagebox.showerror("Error", "All fields must be filled.")
        return

    add_seconds = int(add_seconds)
    filter_users = filter_users.split(',')

    show_progress_bars()

    start_button.grid_forget()

    download_progress['value'] = 0
    read_progress['value'] = 0
    filter_progress['value'] = 0

    filtered_messages = []
    output_filename = ""
    filtering_complete = False

    while not filtering_complete:
        filtered_messages, output_filename, filtering_complete = process_chat(vod_url, add_seconds, filter_users)

    hide_text_area_and_progress_bars()

start_button.config(command=start_processing)
    
def validate_url(url):
    regex_pattern = r'^https:\/\/www\.twitch\.tv\/videos\/\d+$'
    return bool(re.match(regex_pattern, url))

def get_video_created_at(vod_id):
    query = {
        'query': f'{{ video(id: "{vod_id}") {{ createdAt }} }}'
    }

    headers = {
        'Client-ID': 'kimne78kx3ncx6brgo4mv6wki5h1ko',
        'Content-Type': 'application/json'
    }

    response = requests.post('https://gql.twitch.tv/gql', headers=headers, data=json.dumps(query))
    json_data = response.json()
    created_at_str = json_data['data']['video']['createdAt']
    return datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%S%z").replace(tzinfo=None)

def download_chat(vod_url, output_path, download_progress):
    twitch_downloader_cli_path = resource_path("TwitchDownloaderCLI.exe")
    command = f'"{twitch_downloader_cli_path}" chatdownload -u {vod_url} -o "{output_path}" --timestamp-format Utc'

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)

    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            print(output.strip())
            progress_match = re.search(r'\[STATUS\] - Downloading (\d+)%', output)
            if progress_match:
                progress_percent = int(progress_match.group(1))
                download_progress['value'] = progress_percent
                download_progress.update()

    process.stdout.close()
    process.wait()
    download_progress['value'] = 100

def read_chat_log(file_path, read_progress_bar):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        total_lines = len(lines)
        read_progress_bar['maximum'] = total_lines
        for index, line in enumerate(lines):
            match = re.match(r'\[(.*?)\] (.*?): (.*)', line)
            if match:
                timestamp_str, username, message = match.groups()
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S %Z")
                yield timestamp, username, message
            read_progress_bar['value'] = (index + 1)
            read_progress_bar.update()

def get_unique_filename(filename):
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filename):
        filename = f"{base}_{counter}{ext}"
        counter += 1
    return filename

def time_to_stream_timecode(timestamp, start_stream_datetime, add_seconds):
    delta = timestamp - start_stream_datetime + timedelta(seconds=add_seconds)
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def clean_username(username):
    return username.strip().lower()

def filter_messages(all_messages, start_stream_datetime, add_seconds, filter_users, filter_progress_bar):
    filter_users = [clean_username(user) for user in filter_users]
    total_messages = len(all_messages)
    if total_messages == 0:
        return [], True
    filter_progress_bar['maximum'] = total_messages
    filtered_messages = []
    for index, (timestamp, username, message) in enumerate(all_messages):
        if clean_username(username) in filter_users or any(message.startswith(f'@{u}') for u in filter_users):
            stream_timecode = time_to_stream_timecode(timestamp, start_stream_datetime, add_seconds)
            filtered_messages.append(f'{stream_timecode} {username}: {message}')
        filter_progress_bar['value'] = (index + 1)
        filter_progress_bar.update()
        print(f"Progress: {(index + 1) / total_messages * 100:.1f}%")
    filter_progress_bar['value'] = 100
    hide_text_area_and_progress_bars()
    display_filtered_messages(filtered_messages)
    return filtered_messages, True

def create_sorted_folder():
    sorted_folder_path = "Sorted"
    if not os.path.exists(sorted_folder_path):
        os.makedirs(sorted_folder_path)
    return sorted_folder_path

def process_chat(vod_url, add_seconds, filter_users):
    if not validate_url(vod_url):
        return "Invalid Twitch VOD URL"

#   chat_log_path = "chat_log.txt"
#   download_chat(vod_url, chat_log_path, download_progress)

    all_messages = list(read_chat_log(chat_log_path, read_progress))

    vod_id = vod_url.split('/videos/')[1]
    start_stream_datetime = get_video_created_at(vod_id)
    sorted_messages, output_filename = filter_messages(all_messages, start_stream_datetime, add_seconds, filter_users, filter_progress)

    return sorted_messages, output_filename

def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        hide_text_area_and_progress_bars()
        app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)

app.mainloop()