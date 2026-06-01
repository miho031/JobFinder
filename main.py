from email.mime import message
import json
import os
import re
import hashlib
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

SEEN_JOBS_FILE = "seen_jobs.json"

URL = "https://www.scdu.hr/student_poslovi"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_value_after_label(lines, label):
    """
    Pronalazi vrijednost koja se nalazi u redu nakon oznake.

    Primjer:
    Mjesto obavljanja posla:
    Dubrovnik
    """
    for index, line in enumerate(lines):
        if line.strip() == label:
            if index + 1 < len(lines):
                return lines[index + 1].strip()

    return None


def get_value_same_line(lines, label):
    """
    Pronalazi vrijednost koja je u istom redu kao oznaka.

    Primjer:
    Objavljeno: 2026-05-28
    """
    for line in lines:
        if line.startswith(label):
            return line.replace(label, "").strip()

    return None


def extract_hourly_rate(rate_text):
    """
    Pretvara tekst poput '7.50 EUR' u broj 7.5
    """
    if not rate_text:
        return None

    match = re.search(r"(\d+(?:[.,]\d+)?)", rate_text)

    if not match:
        return None

    return float(match.group(1).replace(",", "."))


def parse_job(job_element):
    """
    Prima jedan HTML element oglasa i pretvara ga u Python dictionary.
    """
    text = job_element.get_text("\n", strip=True)
    lines = text.split("\n")

    company = lines[0] if lines else None
    rate_text = get_value_after_label(lines, "Cijena sata:")

    job = {
        "company": company,
        "published": get_value_same_line(lines, "Objavljeno:"),
        "expires": get_value_same_line(lines, "Oglas isteće:"),
        "location": get_value_after_label(lines, "Mjesto obavljanja posla:"),
        "job_type": get_value_after_label(lines, "Vrsta posla:"),
        "description": get_value_after_label(lines, "Opis posla:"),
        "work_period": get_value_after_label(lines, "Period rada:"),
        "work_time": get_value_after_label(lines, "Radno vrijeme:"),
        "hourly_rate_text": rate_text,
        "hourly_rate": extract_hourly_rate(rate_text),
        "email": get_value_after_label(lines, "Email:"),
        "contact_person": get_value_after_label(lines, "Kontakt osoba:"),
        "contact_number": get_value_after_label(lines, "Kontakt broj:"),
        "raw_text": text,
    }

    return job


def fetch_jobs():
    """
    Dohvaća stranicu Student servisa i vraća listu oglasa.
    """
    response = requests.get(URL, headers=HEADERS, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    job_elements = soup.select(".div_dostupni_poslovi")

    jobs = []

    for element in job_elements:
        job = parse_job(element)
        jobs.append(job)

    return jobs


def is_good_job(job):
    """
    Jednostavan filter za dobre oglase.

    Za sada:
    - satnica mora biti barem 7 EUR
    - izbacujemo neke loše ključne riječi
    """
    if job["hourly_rate"] is None:
        return False

    if job["hourly_rate"] < 7.0:
        return False

    bad_keywords = [
        "skladište",
        "pretovar",
        "konobar",
        "zračna luka",
        "Čilipi",
        "teški fizički",
        "fizički",
    ]

    text = job["raw_text"].lower()

    for keyword in bad_keywords:
        if keyword in text:
            return False

    return True


def print_job(job, index):
    """
    Ljepši ispis jednog oglasa u terminal.
    """
    print(f"OGLAS #{index}")
    print(f"Firma: {job['company']}")
    print(f"Objavljeno: {job['published']}")
    print(f"Istječe: {job['expires']}")
    print(f"Lokacija: {job['location']}")
    print(f"Vrsta posla: {job['job_type']}")
    print(f"Opis: {job['description']}")
    print(f"Period rada: {job['work_period']}")
    print(f"Radno vrijeme: {job['work_time']}")
    print(f"Satnica: {job['hourly_rate_text']}")
    print(f"Email: {job['email']}")
    print(f"Kontakt osoba: {job['contact_person']}")
    print(f"Kontakt broj: {job['contact_number']}")
    print("-" * 60)


def create_job_id(job):
    """
    Stvara jedinstveni ID za oglas na temelju njegovih podataka.
    """
    unique_text = f"{job['company']}|{job['job_type']}|{job['published']}|{job['location']}|{job['hourly_rate_text']}"

    return hashlib.md5(unique_text.encode("utf-8")).hexdigest()


def load_seen_jobs():
    """
    Učitava ID-jeve već viđenih oglasa iz seen_jobs.json.
    Ako file ne postoji, vraća prazan set.
    """
    if not os.path.exists(SEEN_JOBS_FILE):
        return set()

    with open(SEEN_JOBS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return set(data)


def save_seen_jobs(seen_jobs):
    """
    Sprema ID-jeve viđenih oglasa u seen_jobs.json.
    """
    with open(SEEN_JOBS_FILE, "w", encoding="utf-8") as file:
        json.dump(list(seen_jobs), file, ensure_ascii=False, indent=2)


def get_new_jobs(jobs, seen_jobs):
    """
    Vraća samo oglase koje još nismo vidjeli.
    """
    new_jobs = []

    for job in jobs:
        job_id = create_job_id(job)
        job["id"] = job_id

        if job_id not in seen_jobs:
            new_jobs.append(job)

    return new_jobs


def send_telegram_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Telegram token ili chat ID nisu postavljeni u .env fileu.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        },
        timeout=10
    )

    response.raise_for_status()


def format_job_message(job):
    return f"""
🟢 <b>Novi dobar studentski posao</b>

<b>Firma:</b> {job['company']}
<b>Lokacija:</b> {job['location']}
<b>Vrsta posla:</b> {job['job_type']}
<b>Opis:</b> {job['description']}
<b>Satnica:</b> {job['hourly_rate_text']}
<b>Radno vrijeme:</b> {job['work_time']}
<b>Period rada:</b> {job['work_period']}

<b>Email:</b> {job['email']}
<b>Kontakt osoba:</b> {job['contact_person']}
<b>Kontakt broj:</b> {job['contact_number']}

https://www.scdu.hr/student_poslovi
""".strip()


def main():
    seen_jobs = load_seen_jobs()

    jobs = fetch_jobs()
    new_jobs = get_new_jobs(jobs, seen_jobs)

    good_new_jobs = [job for job in new_jobs if is_good_job(job)]

    print(f"Ukupno pronađeno oglasa: {len(jobs)}")
    print(f"Novih oglasa: {len(new_jobs)}")
    print(f"Dobrih novih oglasa nakon filtera: {len(good_new_jobs)}")
    print("=" * 60)

    for index, job in enumerate(good_new_jobs, start=1):
        print_job(job, index)

        message = format_job_message(job)
        send_telegram_message(message)

    for job in new_jobs:
        seen_jobs.add(job["id"])

    save_seen_jobs(seen_jobs)


if __name__ == "__main__":
    main()
