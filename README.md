# JD_Resume_analyzer — Multi-JD / Multi-Resume Telegram Bot

This version accepts any practical number of Job Descriptions and resumes supplied by the user, identifies each uploaded document automatically, and performs a cross-product analysis: **every resume is compared against every JD**.

## Flow
1. `/start`
2. Send any JD(s) and resume(s), in any order.
3. The bot classifies each document as JD, resume, or unknown.
4. Unknown/ambiguous documents are rejected and not saved.
5. `/analyze`
6. Every resume × every JD is analyzed.

No OpenAI API is required.

## Setup
```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
```
Create `.env`:
```text
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN
```
Run:
```bash
python bot.py
```

## Important
The ATS score is an explainable estimate based on the submitted JD and resume. It is not a guarantee of any employer's actual ATS result.

## Author
R. Jathin Kumar Reddy
