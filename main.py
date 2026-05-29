import re
import requests
from bs4 import BeautifulSoup

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
        "selidbe",
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


def main():
    jobs = fetch_jobs()

    print(f"Ukupno pronađeno oglasa: {len(jobs)}")

    good_jobs = [job for job in jobs if is_good_job(job)]

    print(f"Dobrih oglasa nakon filtera: {len(good_jobs)}")
    print("=" * 60)

    for index, job in enumerate(good_jobs, start=1):
        print_job(job, index)


if __name__ == "__main__":
    main()
