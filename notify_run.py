#!/usr/bin/env python

import subprocess
import smtplib
import os
import sys
import platform
import configparser
import datetime
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import tempfile
from pathlib import Path
import py7zr
import shutil

# Configuration file path
CONFIG_FILE = os.path.expanduser("~/.notify_run")

def create_config():
    if not os.path.exists(CONFIG_FILE):
        # Create a default configuration file
        default_config = configparser.ConfigParser()
        default_config["SMTP"] = {"server": "smtp.gmail.com", "port": "587", "user": "", "password": ""}
        default_config["Notification"] = {"to_address": ""}
        default_config.write(open(CONFIG_FILE, "w"))
        print(f"Configuration file created at {CONFIG_FILE}.")

def load_config():
    config = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        print(f"Configuration file {CONFIG_FILE} not found.")
        sys.exit(1)
    config.read(CONFIG_FILE)
    return config

def send_email(subject, body, to_address, smtp_server, smtp_port, smtp_user, smtp_password, attachments=[]):
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_address
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    for attachment in attachments:
        with open(attachment, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(attachment)}",
            )
            msg.attach(part)

    try:
        session = smtplib.SMTP(smtp_server, smtp_port)
        session.starttls()
        session.login(smtp_user, smtp_password)
        session.sendmail(smtp_user, to_address, msg.as_string())
        session.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
    return True


def execute_command(command):
    start_time = datetime.datetime.now()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    stdout_log = []
    stderr_log = []
    
    # Function to handle real-time output
    def read_output(pipe, prefix, log):
        for line in iter(pipe.readline, ''):
            print(f'[{prefix}]{line}', end='')
            log.append(line)  # Keep log of the output
            
    # Create threads to read stdout and stderr in real-time and log them
    stdout_thread = threading.Thread(target=read_output, args=(process.stdout, 'O', stdout_log))
    stderr_thread = threading.Thread(target=read_output, args=(process.stderr, 'E', stderr_log))

    stdout_thread.start()
    stderr_thread.start()

    # Wait for the process to complete and the threads to finish
    stdout_thread.join()
    stderr_thread.join()

    process.stdout.close()
    process.stderr.close()
            
    end_time = datetime.datetime.now()
    stdout_log_str = ''.join(stdout_log)
    stderr_log_str = ''.join(stderr_log)

    duration = end_time - start_time
    return process.returncode, stdout_log_str, stderr_log_str, start_time, end_time, duration

def compress_logs(text:str, tmpdir: os.PathLike, file_name:str):
    tmpdir_path = Path(tmpdir)
    tmpdir_path.mkdir(parents=True, exist_ok=True)
    
    log_file = tmpdir_path / f'{file_name}.txt'
    log_zip = tmpdir_path / f'{file_name}.7z'
    
    log_file.absolute().write_text(text)
    with py7zr.SevenZipFile(log_zip, 'w') as archive:
        archive.write(log_file, log_file.name)
    log_file.unlink(missing_ok=True)
    print(log_file)
    return log_zip

def main():
    create_config()
    if len(sys.argv) < 2:
        print("Usage: python notify_run.py <command>")
        sys.exit(1)

    command = " ".join(sys.argv[1:])
    config = load_config()

    host_name = platform.node()
    smtp_server = config["SMTP"]["server"]
    smtp_port = config["SMTP"].getint("port")
    smtp_user = config["SMTP"]["user"]
    smtp_password = config["SMTP"]["password"]
    to_address = config["Notification"]["to_address"]

    returncode, stdout, stderr, start_time, end_time, duration = execute_command(command)

    email_subject = f"Host: '{host_name}' Completed with Return Code {returncode}"
    email_body_header = f"""================
NotifyRun
================
Command: {command}
Return Code: {returncode}

Start Time: {start_time}
End Time: {end_time}
Duration: {duration}
"""
    if duration < datetime.timedelta(seconds=10):
        print(f"Skipping email notification as the command completed in less than 10 seconds.")
        print(email_body_header)
        sys.exit(returncode)

    tempdir = tempfile.TemporaryDirectory('notifyrun')
    try:
        if len(stdout) + len(stderr) > 10:
            # Compress logs if they are too large
            stdout_zip = compress_logs(stdout, tempdir.name, 'stdout')
            stderr_zip = compress_logs(stderr, tempdir.name, 'stderr')
            attachments = [stdout_zip, stderr_zip]
            email_body = f"{email_body_header}\nStandard Output and Error are attached as compressed files.\n"
        else:
            email_body = f"{email_body_header}\nStandard Output:\n{stdout}\nStandard Error:\n{stderr}\n"
        
        if not send_email(email_subject, email_body, to_address, smtp_server, smtp_port, smtp_user, smtp_password, attachments):
            print(f"Error sending email, Temporary files are stored at {tempdir.name}")
            print("Trying the fallback method...")
            email_body = f"{email_body_header}\nError sending email, Temporary files are stored at {tempdir.name}"
            if not send_email(email_subject, email_body, to_address, smtp_server, smtp_port, smtp_user, smtp_password, []):
                print("Error sending email, please check the configuration.")
        else:
            tempdir.cleanup()
    except Exception as e:
        print(f"Error during email preparation: {e}")
        print(f"Temporary files are stored at {tempdir.name}")
    
    sys.exit(returncode)


if __name__ == "__main__":
    main()
