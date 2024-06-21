#!/usr/bin/env python

import subprocess
import smtplib
import os
import sys
import configparser
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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


def send_email(subject, body, to_address, smtp_server, smtp_port, smtp_user, smtp_password):
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_address
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        session = smtplib.SMTP(smtp_server, smtp_port)
        session.starttls()
        session.login(smtp_user, smtp_password)
        session.sendmail(smtp_user, to_address, msg.as_string())
        session.quit()
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")


def execute_command(command):
    start_time = datetime.datetime.now()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = process.communicate()
    end_time = datetime.datetime.now()

    duration = end_time - start_time
    return process.returncode, stdout, stderr, start_time, end_time, duration


def main():
    create_config()
    if len(sys.argv) < 2:
        print("Usage: python notify_run.py <command>")
        sys.exit(1)

    command = " ".join(sys.argv[1:])
    config = load_config()

    host_name = os.uname()[1]
    smtp_server = config["SMTP"]["server"]
    smtp_port = config["SMTP"].getint("port")
    smtp_user = config["SMTP"]["user"]
    smtp_password = config["SMTP"]["password"]
    to_address = config["Notification"]["to_address"]

    returncode, stdout, stderr, start_time, end_time, duration = execute_command(command)

    email_subject = f"Host: '{host_name}' Completed with Return Code {returncode}"
    email_body = f"""
Command: {command}
Return Code: {returncode}

Start Time: {start_time}
End Time: {end_time}
Duration: {duration}

Standard Output:
{stdout}

Standard Error:
{stderr}
"""

    send_email(email_subject, email_body, to_address, smtp_server, smtp_port, smtp_user, smtp_password)

    print(stdout)
    if stderr:
        print(stderr, file=sys.stderr)
    sys.exit(returncode)


if __name__ == "__main__":
    main()
