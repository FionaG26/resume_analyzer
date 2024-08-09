from flask import Flask, render_template, request, jsonify
import re
from spellchecker import SpellChecker
from textblob import TextBlob
import pandas as pd
import spacy
import docx2txt
import PyPDF2
import os

app = Flask(__name__)

# Initialize NLP model
nlp = spacy.load("en_core_web_sm")

# Function to extract raw text from a resume (PDF, Word, etc.)


def extract_text_from_file(file_path):
    if file_path.endswith('.docx'):
        return docx2txt.process(file_path)
    elif file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    else:
        raise ValueError(
            "Unsupported file format. Please upload a .docx or .pdf file.")


def extract_text_from_pdf(file_path):
    pdf_text = ""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            pdf_text += page.extract_text()
    return pdf_text

# Resume Parsing Functions


def extract_contact_info(resume_text):
    contact_info = {}
    contact_info['email'] = re.findall(r'\S+@\S+', resume_text)
    contact_info['phone'] = re.findall(r'\b\d{10,15}\b', resume_text)
    contact_info['linkedin'] = re.findall(r'(https?://[^\s]+)', resume_text)
    return contact_info


def extract_sections(resume_text):
    sections = {}
    sections['work_experience'] = re.findall(
        r'(?<=Work Experience)(.*?)(?=Education)', resume_text, re.DOTALL)
    sections['education'] = re.findall(
        r'(?<=Education)(.*?)(?=Skills|Experience|$)',
        resume_text,
        re.DOTALL)
    sections['skills'] = re.findall(
        r'(?<=Skills)(.*?)(?=Experience|Education|$)',
        resume_text,
        re.DOTALL)
    return sections

# Keyword Matcher


def keyword_matcher(resume_text, job_description):
    def preprocess_text(text): return re.sub(r'\W+', ' ', text.lower())
    resume_text_cleaned = preprocess_text(resume_text)
    job_description_cleaned = preprocess_text(job_description)

    resume_keywords = set([token.text.lower() for token in nlp(
        resume_text_cleaned) if not token.is_stop and not token.is_punct])
    job_keywords = set([token.text.lower() for token in nlp(
        job_description_cleaned) if not token.is_stop and not token.is_punct])

    matched_keywords = resume_keywords & job_keywords
    missing_keywords = job_keywords - resume_keywords
    keyword_density = len(matched_keywords) / \
        len(job_keywords) if job_keywords else 0

    return len(matched_keywords), len(missing_keywords), keyword_density

# Experience Evaluator


def experience_evaluator(work_experience_section, job_description):
    experience_titles = re.findall(
        r'\b(?:Manager|Analyst|Engineer|Scientist|Developer|Technician)\b',
        work_experience_section[0])
    job_titles = re.findall(
        r'\b(?:Manager|Analyst|Engineer|Scientist|Developer|Technician)\b',
        job_description)
    matched_titles = set(experience_titles) & set(job_titles)
    return len(matched_titles), matched_titles

# Skills Assessor


def skills_assessor(resume_skills, job_skills):
    matched_skills = resume_skills & job_skills
    missing_skills = job_skills - resume_skills
    return len(matched_skills), len(missing_skills)

# Education Verifier


def education_verifier(education_section, required_degree):
    education_degrees = re.findall(
        r'\b(Bachelor|Master|PhD)\b',
        education_section[0])
    return any(required_degree.lower() in degree.lower()
               for degree in education_degrees)

# Format Analyzer


def format_analyzer(resume_text):
    has_simple_format = all([
        # No tabs or double line breaks
        not bool(re.search(r'\t|\n{2,}', resume_text)),
        not bool(re.search(r'<[^>]*>', resume_text))  # No HTML tags
    ])
    return has_simple_format

# Achievements Analyzer


def achievements_analyzer(resume_text):
    achievements = re.findall(
        r'\b(increased|reduced|improved|saved|achieved|grew|generated)\b.*?(\d+%)',
        resume_text,
        re.I)
    return len(achievements)


# Language Checker
spell = SpellChecker()


def language_checker(resume_text):
    words = resume_text.split()
    misspelled = spell.unknown(words)

    # Grammar check using TextBlob
    blob = TextBlob(resume_text)
    grammatical_errors = []
    for sentence in blob.sentences:
        corrected_sentence = sentence.correct()
        if sentence != corrected_sentence:
            grammatical_errors.append((str(sentence), str(corrected_sentence)))

    return len(misspelled), grammatical_errors

# Diversity & Inclusion Assessor


def diversity_inclusion_assessor(resume_text):
    diversity_keywords = [
        "diverse",
        "inclusion",
        "overcame adversity",
        "socio-economic challenges",
        "first-generation",
        "immigration",
        "LGBTQ+",
        "underrepresented",
        "minority",
        "disability"]
    diversity_mentions = [
        word for word in diversity_keywords if word.lower() in resume_text.lower()]

    return len(diversity_mentions)

# Overall Scorer


def overall_scorer(
        keyword_score,
        experience_score,
        skills_score,
        education_verifier,
        format_check,
        achievements,
        language_errors,
        diversity_mentions):
    score = (keyword_score[0] + experience_score[0] +
             skills_score[0] + (10 if education_verifier else 0)) / 40
    score += achievements * 2  # Each achievement adds 2 points
    # Each spelling mistake reduces the score by 0.5 points
    score -= language_errors[0] * 0.5
    score += diversity_mentions * 2  # Each diversity mention adds 2 points

    if format_check:
        return score * 10
    return (score * 10) - 5


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    resume_file = request.files.get('resume')
    job_description = request.form.get('job_description')

    if not resume_file:
        return jsonify({'error': 'No resume file provided.'}), 400

    # Save the file
    file_path = os.path.join('uploads', resume_file.filename)
    resume_file.save(file_path)

    try:
        resume_text = extract_text_from_file(file_path)
        sections = extract_sections(resume_text)

        print("Extracted Sections:", sections)  # Debugging line
                
        work_experience_section = sections.get('work_experience', [""])[0]
        education_section = sections.get('education', [""])[0]
        skills_section = sections.get('skills', [""])[0]

        # Job description (example)
        # Ideally, this would be dynamic or from a database
        job_description = request.form.get('job_description', '')

        # Perform checks
        keyword_score = keyword_matcher(resume_text, job_description)
        experience_score = experience_evaluator(
            sections['work_experience'], job_description)
        skills_score = skills_assessor(set(sections['skills'][0].split()), {
                                       'genomics', 'data analysis', 'R', 'biology'})
        education_check = education_verifier(
            sections['education'], 'Bachelor of Science')
        format_check = format_analyzer(resume_text)
        achievements = achievements_analyzer(resume_text)
        misspelled_words, grammatical_errors = language_checker(resume_text)
        diversity_mentions = diversity_inclusion_assessor(resume_text)

        # Calculate final score
        final_score = overall_scorer(
            keyword_score, experience_score, skills_score,
            education_check, format_check, achievements,
            (misspelled_words, grammatical_errors), diversity_mentions
        )

        return jsonify({
            'keyword_score': keyword_score[2] * 100,
            'experience_score': experience_score[0] * 100,
            'skills_score': skills_score[0] * 100,
            'education_check': 100 if education_check else 0,
            'format_check': 100 if format_check else 0,
            'achievements': achievements,
            'misspelled_words': ', '.join(misspelled_words),
            'grammatical_errors': '; '.join([f"{orig} -> {corr}" for orig, corr in grammatical_errors]),
            'diversity_mentions': diversity_mentions,
            'final_score': final_score
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
